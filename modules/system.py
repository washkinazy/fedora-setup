"""System configuration: dnf.conf tuning, sysctl, zram swap."""

import subprocess

from pyinfra.context import host
from pyinfra.facts.hardware import Memory
from pyinfra.operations import dnf, files, server, systemd
from pyinfra.operations.util import any_changed


def _zram_active():
    """Check whether a zram swap device is currently running."""
    result = subprocess.run(
        ["bash", "-c", "swapon --show=NAME --noheadings | grep -q '^/dev/zram'"],
        check=False,
    )
    return result.returncode == 0


# --- dnf configuration ---

files.line(
    name="Disable weak dependencies",
    path="/etc/dnf/dnf.conf",
    line="install_weak_deps=False",
    replace="install_weak_deps=.*",
)

# --- Name resolution ---

resolved_mdns = files.put(
    name="Enable resolve-only mDNS in systemd-resolved",
    src="files/60-mdns-resolved.conf",
    dest="/etc/systemd/resolved.conf.d/60-mdns.conf",
    user="root",
    group="root",
    mode="0644",
)

networkmanager_mdns = files.put(
    name="Enable resolve-only mDNS for NetworkManager connections",
    src="files/60-mdns-networkmanager.conf",
    dest="/etc/NetworkManager/conf.d/60-mdns.conf",
    user="root",
    group="root",
    mode="0644",
)

systemd.service(
    name="Restart systemd-resolved after mDNS configuration",
    service="systemd-resolved.service",
    running=True,
    restarted=True,
    _if=any_changed(resolved_mdns, networkmanager_mdns),
)

server.shell(
    name="Apply resolve-only mDNS to active network links",
    commands=[
        "nmcli general reload conf",
        (
            "nmcli -t -f DEVICE,TYPE,STATE device status"
            ' | awk -F: \'$3 == "connected" && ($2 == "ethernet" || $2 == "wifi")'
            " { print $1 }'"
            " | xargs -r -n1 nmcli device reapply"
        ),
    ],
    _if=any_changed(resolved_mdns, networkmanager_mdns),
)

# --- System tuning ---

sysctl_config = files.put(
    name="Deploy custom sysctl settings",
    src="files/99-custom-sysctl.conf",
    dest="/etc/sysctl.d/99-custom.conf",
    user="root",
    group="root",
    mode="0644",
)

server.shell(
    name="Reload sysctl",
    commands=["sysctl --system"],
    _if=[sysctl_config.did_change],
)

# --- zram swap ---

dnf.packages(
    name="Install zram-generator",
    packages=["zram-generator"],
)

zram_config = files.template(
    name="Configure zram swap device",
    src="templates/zram-generator.conf.j2",
    dest="/etc/systemd/zram-generator.conf",
    user="root",
    group="root",
    mode="0644",
    zram_size_mb=host.get_fact(Memory) // 2,
)

# Rerun generators after changing the zram configuration.
systemd.daemon_reload(
    name="Reload systemd daemon for zram",
    _if=[zram_config.did_change],
)

# Resizing an active swap device may require a reboot.
systemd.service(
    name="Activate zram swap device",
    service="systemd-zram-setup@zram0.service",
    running=True,
    restarted=_zram_active(),
    _if=[zram_config.did_change],
)

"""System configuration: dnf.conf tuning, sysctl, zram swap."""

import subprocess

from pyinfra.context import host
from pyinfra.facts.hardware import Memory
from pyinfra.operations import dnf, files, server, systemd
from pyinfra.operations.util import any_changed


def _zram_active():
    """Check whether a zram swap device is currently running.

    Only chooses between starting and restarting the unit. It must never gate
    the config itself: that tests runtime device state to decide whether to
    render a config file, which freezes the sizing on any machine that already
    has a zram device.
    """
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
#
# Fedora resolves .local names through Avahi/nss-mdns on the host, but Flatpak
# runtimes use nss-resolve through systemd-resolved instead. Enable resolution
# only (not announcing) in both resolved and NetworkManager so sandboxed apps
# can resolve the same mDNS names without competing with Avahi.

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
# Sized at deploy time to ~50% of detected RAM (compressed in-RAM swap). This is
# what makes the high vm.swappiness in the sysctl config above sane.
#
# The package and the config are ensured unconditionally — never behind a check
# for a running zram device, which would gate config-file state on runtime device
# state and leave the sizing frozen on any machine that already has one.

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

# zram-generator builds the unit from the config, so the generators must be
# re-run before the device can pick up a new size.
systemd.daemon_reload(
    name="Reload systemd daemon for zram",
    _if=[zram_config.did_change],
)

# Restart rather than start: a running device keeps its original size until the
# unit is recreated. Resizing needs the swap to be empty, so on a busy system
# this effectively lands on the next reboot.
systemd.service(
    name="Activate zram swap device",
    service="systemd-zram-setup@zram0.service",
    running=True,
    restarted=_zram_active(),
    _if=[zram_config.did_change],
)

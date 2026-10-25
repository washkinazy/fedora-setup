"""Network and local storage mount configuration."""

import os
import subprocess

from pyinfra.context import host
from pyinfra.operations import dnf, files, server, systemd

features = host.data.get("features") or {}


def _unit_stem(path):
    """Return the systemd-escaped unit-name stem for a mount path."""
    result = subprocess.run(
        ["systemd-escape", "--path", path],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


# --- Synology NAS CIFS mounts ---

if features.get("synology"):
    # cifs-utils lives here rather than in PACKAGES because this module runs
    # before modules/packages.py — anything the mounts depend on has to be
    # installed by the module that needs it.
    dnf.packages(
        name="Install cifs-utils",
        packages=["cifs-utils"],
    )

    for mount in host.data.get("storage_mounts") or []:
        stem = _unit_stem(mount["where"])

        mount_unit = files.template(
            name=f"Deploy {mount['name']} mount unit",
            src="templates/synology-mount-unit.j2",
            dest=f"/etc/systemd/system/{stem}.mount",
            user="root",
            group="root",
            mode="0644",
            item=mount,
            hostname=host.data.get("hostname"),
        )

        automount_unit = files.template(
            name=f"Deploy {mount['name']} automount unit",
            src="templates/synology-automount-unit.j2",
            dest=f"/etc/systemd/system/{stem}.automount",
            user="root",
            group="root",
            mode="0644",
            item=mount,
        )

        files.directory(
            name=f"Create {mount['where']} directory",
            path=mount["where"],
            user="root",
            group="root",
            mode="0755",
        )

        # running=True as well as enabled=True: an automount that is enabled but
        # not started never triggers a mount.
        units_changed = mount_unit.will_change or automount_unit.will_change
        systemd.service(
            name=f"Enable {mount['name']} automount",
            service=f"{stem}.automount",
            running=True,
            enabled=True,
            restarted=units_changed,
            daemon_reload=units_changed,
        )

# --- Local disk mounts (BTRFS subvolumes) — mounted at boot with nofail ---
# Skip any device that isn't currently attached (UUID not present).

# Create any shared groups referenced by local mounts before chowning the
# mountpoints to them.
for group_name in sorted(
    {m["dir_group"] for m in (host.data.get("local_mounts") or []) if m.get("dir_group")}
):
    server.group(
        name=f"Create {group_name} group",
        group=group_name,
    )

for mount in host.data.get("local_mounts") or []:
    if not os.path.exists(f"/dev/disk/by-uuid/{mount['uuid']}"):
        continue

    stem = _unit_stem(mount["where"])

    mount_unit = files.template(
        name=f"Deploy {mount['name']} local mount unit",
        src="templates/local-mount-unit.j2",
        dest=f"/etc/systemd/system/{stem}.mount",
        user="root",
        group="root",
        mode="0644",
        item=mount,
    )

    files.directory(
        name=f"Create {mount['where']} directory",
        path=mount["where"],
        user="root",
        group=mount.get("dir_group", "root"),
        mode=mount.get("dir_mode", "0755"),
    )

    # restarted= is the important part: with only running=True a changed unit is
    # daemon-reloaded but systemd sees it already active and does nothing, so new
    # Options=/What= were written to disk and never actually applied.
    systemd.service(
        name=f"Mount {mount['name']}",
        service=f"{stem}.mount",
        running=True,
        enabled=True,
        restarted=mount_unit.will_change,
        daemon_reload=mount_unit.will_change,
    )

# --- Polkit to make mounts easier. ---

polkit_rules = files.put(
    name="Polkit rule: wheel group can mount without password",
    src="files/50-udisks-wheel.rules",
    dest="/etc/polkit-1/rules.d/50-udisks-wheel.rules",
    user="root",
    group="root",
    mode="0644",
)

systemd.service(
    name="Restart polkit",
    service="polkit",
    restarted=True,
    _if=[polkit_rules.did_change],
)

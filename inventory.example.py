"""Example host inventory.

Copy this file to inventory.py and customize it. inventory.py is ignored by Git
because it commonly contains private machine, storage, and account details.
"""

host_data = {
    "hostname": "fedora-workstation",
    "features": {
        "development": True,
        "gaming": False,
        "synology": False,
        "tailscale": False,
    },
    # A True entry enables the repository and its source-specific packages.
    # A False or omitted entry disables the repository and excludes those packages.
    "repos": {
        "rpmfusion_nonfree_steam": False,
        "rpmfusion_nonfree_nvidia_driver": False,
        "rpmfusion_free": False,
        "rpmfusion_nonfree": False,
        "terra": False,
        "terra_nvidia": False,
        "terra_extras": False,
        "terra_mesa": False,
        "terra_multimedia": False,
        "fedora_cisco_openh264": True,
        "copr_niri": False,
        "copr_hyprland": False,
        "gh_cli": False,
        "vscodium": True,
        "tailscale": False,
        "negativo17_nvidia": False,
        "negativo17_spotify": False,
        "negativo17_multimedia": False,
    },
    "desktop_environments": {
        "niri": False,
        "hyprland": False,
        "kde": True,
        "cosmic": False,
        "gnome": False,
    },
    # Example network mount:
    # {"name": "media", "what": "//nas.local/media", "where": "/synology/media"}
    "storage_mounts": [],
    # Example local mount:
    # {
    #     "name": "data",
    #     "uuid": "00000000-0000-0000-0000-000000000000",
    #     "where": "/storage/data",
    #     "fstype": "btrfs",
    #     "options": "subvol=@data",
    #     "dir_group": "storage",
    #     "dir_mode": "2775",
    # }
    "local_mounts": [],
    # Leave username empty to skip account changes.
    "user_config": {
        "username": "",
        "full_username": "",
    },
    "user_groups": [],
}

hosts = [
    ("@local", host_data),
]

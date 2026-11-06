"""Example host inventory.

Copy this file to inventory.py and customize it. inventory.py is ignored by Git
because it commonly contains private machine, storage, and account details.
"""

host_data = {
    "hostname": "fedora-workstation",
    "features": {
        "development": True,
        "gaming": False,
        "tailscale": False,
    },
    "desktop_environments": {
        "niri": False,
        "hyprland": True,
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

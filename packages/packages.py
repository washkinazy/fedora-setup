"""Package lists for system, desktop, development, and gaming.

Groups are split by source. NAME holds what the official Fedora repos carry, and
NAME_<REPO> holds packages for which that third-party repository (a key of REPOS
in packages/repos.py, upper-cased) is the only source. A package that both Fedora
and a third-party repo ship stays in the base list — dnf resolves the newer build
— with a comment naming the other source.

modules/packages.py includes each NAME_<REPO> half only when its repository
toggle is enabled. Only groups that actually draw from a third-party repo have a
half for it, since an empty half per repo per group would drown the lists. Fedora
package groups (`@name`) and Flatpak ids are not split — the former are official
by definition and the latter resolve from Flathub, not dnf.
"""


def with_repo_packages(base, toggles, *repo_groups):
    """Return base plus package groups whose repository toggle is enabled."""
    selected = list(base)
    for repo_keys, packages in repo_groups:
        if any(toggles.get(key, False) for key in repo_keys):
            selected.extend(packages)
    return selected


# --- Base system ---

PACKAGE_GROUPS = [
    "@base-graphical",
    "@core",
    "@fonts",
    "@hardware-support",
    "@networkmanager-submodules",
    "@printing",
    "@standard",
]

PACKAGES = [
    # Firmware & microcode
    "linux-firmware",
    "amd-gpu-firmware",
    "amd-ucode-firmware",
    "intel-gpu-firmware",
    "nvidia-gpu-firmware",
    "microcode_ctl",
    # Core system
    "sudo",
    "systemd-udev",
    "openssl",
    "bash-completion",
    # Power
    "tuned",
    "tuned-ppd",
    # Shell & CLI utilities
    "vim",
    "git",
    "curl",
    "wget2-wget",
    "rsync",
    "chezmoi",
    "trash-cli",
    "cabextract",
    "mc",
    # System monitoring & info
    "btop",
    "nvtop",
    "nmon",
    "duf",
    "ncdu",
    "hwinfo",
    "inxi",
    "fastfetch",
    # Printing
    "hplip",
    "system-config-printer",
    # Multimedia libraries
    "libmediainfo",
    "libva",
    "libva-utils",
    # Desktop portals
    "xdg-desktop-portal",
    "xdg-desktop-portal-gtk",
    # Qt Wayland
    "qt6-qtwayland",
    "qt5-qtwayland",
    # Filesystems & VFS
    "gvfs",
    "gvfs-smb",
    "fuse",
    "fuse-libs",
]

# Terra names its Nerd Fonts builds <family>-nerd-fonts (one package per family,
# `nerd-fonts` for the whole set) and ships Iosevka as belleve-invis-iosevka-*.
FONTS_TERRA = [
    # Nerd Fonts
    "firacode-nerd-fonts",
    "cascadiacode-nerd-fonts",
    "jetbrainsmono-nerd-fonts",
    "iosevka-nerd-fonts",
    # Iosevka proper (unpatched); -fonts-all pulls every variant
    "belleve-invis-iosevka-fonts",
]

FONTS = [
    "fontawesome-6-free-fonts",
    "fontawesome-6-brands-fonts",
    "fontawesome4-fonts",
    "fontawesome4-fonts-web",
    "rsms-inter-fonts",
    "rsms-inter-vf-fonts",
]

FLATPAK_MANAGEMENT = [
    "com.github.tchx84.Flatseal",
    "io.github.flattool.Warehouse",
]

# --- GPU drivers ---
# Selected at deploy time from the GPUs actually on the PCI bus; see
# modules/hardware.py. AMD and Intel need nothing here: their kernel drivers are
# in-tree, Mesa is pulled in by @base-graphical and the firmware is in PACKAGES.

# Negativo17's standalone NVIDIA stack. `akmod-nvidia` is the open kernel module (built
# from NVIDIA's kernel-module-source `kernel-open/` tree) as an akmod: built
# against the running kernel, signed with the akmods MOK key on Secure Boot
# systems, and the initramfs regenerated. It is listed explicitly because
# nvidia-kmod-common only requires *a* provider of nvidia-kmod, and dnf would
# otherwise pick between the akmod, dkms and prebuilt kmod variants itself.
# The CUDA-repo `nvidia-open` package does none of the akmod work, and mixing it
# with a distro-built driver produced version-mismatched modules that failed
# NVKMS init.
NVIDIA_NEGATIVO17_NVIDIA = [
    "akmod-nvidia",
    "nvidia-driver",
    "nvidia-driver-cuda",
    "nvidia-persistenced",  # daemon enabled in modules/hardware.py
]

NVIDIA = [
    *NVIDIA_NEGATIVO17_NVIDIA,
]

# --- Desktop environment ---
# Mirrors the arch-setup layout: WAYLAND_WM_COMMON holds only what Noctalia does
# not provide, NOCTALIA is the shell, and each compositor list splats both in.
# Fedora names differ from Arch's in places; the Arch name is noted inline.

WAYLAND_WM_COMMON_TERRA_OR_COPR_HYPRLAND = [
    # Also in copr_hyprland; not in Fedora proper.
    "uwsm",
]

WAYLAND_WM_COMMON_TERRA = [
    # The shared dotfiles provide a user service that inhibits idle while audio plays.
    "sway-audio-idle-inhibit",
]

# Session-level pieces that Noctalia does NOT provide, splatted into every
# compositor below. The bar, launcher, notifications, wallpaper, lockscreen, idle
# handling and the network/bluetooth/audio applets are the shell's job — see
# NOCTALIA.
WAYLAND_WM_COMMON = [
    # Authentication & secrets
    "kf6-kwallet",  # arch: kwallet
    "pam-kwallet",  # arch: kwallet-pam
    "polkit-kde",  # arch: polkit-kde-agent
    # Session startup commands used by the shared niri/Hyprland dotfiles
    "xdg-user-dirs",
    "xdg-user-dirs-gtk",
    # Backends the shell drives rather than replaces
    "brightnessctl",
    "playerctl",
    # Qt/GTK application theming (Noctalia themes itself, not your Qt apps)
    "qt6ct",
    "qt5ct",
]

# Noctalia is the desktop shell for both Wayland compositors below. Fedora 44+
# packages it; the lionheartp/Hyprland COPR also carries noctalia-shell,
# noctalia-git and a v5 pre-release. Verify the name on the live system.
# power-profiles-daemon is a listed optdep but is deliberately absent: tuned-ppd
# in PACKAGES already provides it and the two conflict.
NOCTALIA = [
    "noctalia",
    "ddcutil",  # optdep: external monitor brightness over DDC/CI
    "upower",  # optdep: battery and power device integration
]

# Minimal desktop environments, not the full workstation package set.
KDE = ["@kde-desktop"]
GNOME = ["@gnome-desktop"]
COSMIC = ["@cosmic-desktop"]

# Base WM package sets.
# niri is in the official repos as well; copr_niri only supplies a newer build,
# so the compositor keeps working with that toggle off.
NIRI = [
    "niri",
    "xwayland-satellite",
    "xdg-desktop-portal-gnome",
    *WAYLAND_WM_COMMON,
    *NOCTALIA,
]

# Based on the arch-setup HYPRLAND list. Fedora proper carries none of these, so
# the whole compositor set is the COPR half. Hyprland has XWayland built in.
# hyprpaper/hyprlock/hypridle are intentionally omitted: Noctalia provides the
# wallpaper, lockscreen and idle roles (see NOCTALIA above).
HYPRLAND_COPR_HYPRLAND = [
    "hyprland",
    "xdg-desktop-portal-hyprland",
    "hyprshutdown",
    "hyprlauncher",
    "hyprsunset",
    "hyprpolkitagent",
    "hyprland-guiutils",
]

HYPRLAND = [
    # The dotfiles autostart this bridge everywhere except niri.
    "xwaylandvideobridge",
    *WAYLAND_WM_COMMON,
    *NOCTALIA,
]

# zed-cli supplies /usr/bin/zed, which upstream's install.sh used to put on PATH.
DESKTOP_APPS_TERRA = [
    "zed",
    "zed-cli",
]

DESKTOP_APPS = [
    # Terminals & shell
    "alacritty",
    "kitty",
    "fish",
    # File manager (Dolphin + KDE integration)
    "dolphin",
    "dolphin-plugins",
    "ark",
    "ffmpegthumbs",
    "kdegraphics-thumbnailers",
    "gnome-disk-utility",
    "udiskie",
    # Archives
    "unzip",
    # Fedora's unrar-free wrapper. RARLAB's unrar is in terra-extras and RPM
    # Fusion nonfree, neither of which is on.
    "unrar",
    "p7zip",
    "p7zip-plugins",
    "zip",
    "bzip2",
    # Used by the fix-jpg-meta and fix-bad-images Fish functions.
    "perl-Image-ExifTool",
    # Media & viewers & editors
    "okular",
    "kate",
    "kwrite",
    "kcalc",
    "gwenview",
    # Office is part of the KDE Spin baseline and stays native.
    "@libreoffice",
    # Firefox is part of the KDE Spin baseline and stays native.
    "firefox",
]

FLATPAK_APPS = [
    "org.mozilla.firefox",
    "org.torproject.torbrowser-launcher",
    "com.discordapp.Discord",
    "com.bitwarden.desktop",
    "it.mijorus.gearlever",
    "hu.irl.cameractrls",
    "fr.handbrake.ghb",
    "com.slack.Slack",
    # Applications beyond the Fedora KDE Spin baseline live in Flatpak.
    "org.chromium.Chromium",
    "app.zen_browser.zen",
    "io.gitlab.librewolf-community",
    "org.videolan.VLC",
    "com.spotify.Client",
    "org.inkscape.Inkscape",
    "org.gimp.GIMP",
    "com.rawtherapee.RawTherapee",
]

# --- Development ---

DEV_PACKAGES = [
    "gh",  # also in gh_cli, which supplies the current upstream release
    "just",
    "go-task",  # the binary is `task`
    "ruff",
    "yamllint",
    "shellcheck",
    "jq",
    "pipx",
]

DEV_PACKAGES_VSCODIUM = [
    "codium",
]

# Language toolchains and their version manager are user-scope concerns and are
# deliberately not managed here.

CONTAINER_TOOLS = [
    "distrobox",
    "podman",
    "podman-compose",
]

VIRTUALIZATION = [
    "@virtualization",
    "libvirt-daemon",
]

FLATPAK_CONTAINER_TOOLS = [
    "io.podman_desktop.PodmanDesktop",
    "io.github.dvlv.boxbuddyrs",
]

# --- Tailscale ---

# Fedora carries tailscale too; the tailscale repo supplies the current upstream
# release, so the install still resolves with that toggle off.
TAILSCALE = [
    "tailscale",
]

# --- Gaming ---

GAMING_PACKAGES = [
    # Vulkan
    "vulkan-loader",
    "vulkan-tools",
    "vulkan-validation-layers",
    # Performance & tooling
    "mangohud",
    "gamescope",
    # Controllers
    "steam-devices",
    "jstest-gtk",
]

GAMING_FLATPAK_APPS = [
    "com.valvesoftware.Steam",
    "com.github.Matoking.protontricks",
    "net.davidotek.pupgui2",
    "com.usebottles.bottles",
    "com.heroicgameslauncher.hgl",
]

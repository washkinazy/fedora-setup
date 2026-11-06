"""Package selections and their required third-party sources.

Fedora supplies packages unless PACKAGE_REPOSITORIES explicitly names a source.
Selections are grouped by purpose; repository mappings only describe sources.
"""


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
    # Additional firmware
    "linux-firmware",
    # Core system
    "openssl",
    # Power
    "tuned",
    "tuned-ppd",
    # Shell & CLI utilities
    "vim",
    "git",
    "chezmoi",
    "trash-cli",
    "cabextract",
    "mc",
    "pipx",
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


FONTS = [
    # Nerd Fonts
    "firacode-nerd-fonts",
    "cascadiacode-nerd-fonts",
    "jetbrainsmono-nerd-fonts",
    "iosevka-nerd-fonts",
    "belleve-invis-iosevka-fonts",
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

# --- Multimedia codecs ---


MULTIMEDIA = [
    "gstreamer1-plugins-base",
    "gstreamer1-plugins-good",
    "gstreamer1-plugins-bad-free",
    "gstreamer1-plugin-libav",
    "gstreamer1-plugin-openh264",
    "ffmpeg",
    "vlc-plugins-freeworld",
    "gstreamer1-plugins-bad-freeworld",
    "gstreamer1-plugins-ugly",
    "openh264",
    "mozilla-openh264",
]

# --- Secret storage ---

KEYRING_GNOME = ["gnome-keyring", "gnome-keyring-pam"]
KEYRING_OO7 = ["oo7-daemon", "oo7-portal", "pam_oo7"]


def keyring_packages(fedora_major):
    if not isinstance(fedora_major, int) or fedora_major < 1:
        raise ValueError("Cannot select keyring packages without a Fedora release version")
    return list(KEYRING_OO7 if fedora_major >= 45 else KEYRING_GNOME)


# --- GPU drivers ---


NVIDIA = [
    "nvidia-open",
]

NVIDIA_BUILD_PACKAGES = ["kernel-devel-matched", "dkms"]

# --- Desktop environment ---


WAYLAND_WM_COMMON = [
    "uwsm",
    "sway-audio-idle-inhibit",
    # Authentication & secrets
    "mate-polkit",
    "xdg-user-dirs",
    "xdg-user-dirs-gtk",
    "brightnessctl",
    "playerctl",
    # Qt/GTK application theming
    "qt6ct",
    "qt5ct",
]

NOCTALIA = [
    "noctalia",
    "ddcutil",
    "upower",
]

KDE = ["@kde-desktop"]
GNOME = ["@gnome-desktop"]
COSMIC = ["@cosmic-desktop"]

NIRI = [
    "niri",
    "xwayland-satellite",
    "xdg-desktop-portal-gnome",
    *WAYLAND_WM_COMMON,
    *NOCTALIA,
]


HYPRLAND = [
    "hyprland",
    "xdg-desktop-portal-hyprland",
    "hyprshutdown",
    "hyprlauncher",
    "hyprsunset",
    "hyprland-guiutils",
    "xwaylandvideobridge",
    *WAYLAND_WM_COMMON,
    *NOCTALIA,
]


DESKTOP_APPS = [
    # Terminals & shell
    "alacritty",
    "kitty",
    "fish",
    # File manager and extensions
    "dolphin",
    "dolphin-plugins",
    "ark",
    "ffmpegthumbs",
    "kdegraphics-thumbnailers",
    "gnome-disk-utility",
    "udiskie",
    # Archives
    "unrar",
    "p7zip",
    "p7zip-plugins",
    "perl-Image-ExifTool",
    # Media & viewers & editors
    "okular",
    "kate",
    "kwrite",
    "kcalc",
    "gwenview",
    # "zathura",
    # "zathura-pdf-poppler",
    # "mousepad",
    # "qalculate-gtk",
    # "ristretto",
    "gimp",
    "inkscape",
    "@libreoffice",
    "@firefox",
    "chromium",
    "librewolf",
    "vlc",
    "rawtherapee",
    "darktable",
]

SLACK_RPM_URL = "https://slack.com/api/desktop.latestRelease?arch=x64&variant=rpm&redirect=true"

FLATPAK_APPS = [
    "org.torproject.torbrowser-launcher",
    "com.discordapp.Discord",
    "com.bitwarden.desktop",
    "it.mijorus.gearlever",
    "hu.irl.cameractrls",
    "fr.handbrake.ghb",
    "app.zen_browser.zen",
    "com.spotify.Client",
]

# --- Development ---

DEV_PACKAGES = [
    "codium",
    "zed",
    "zed-cli",
    "gh",
    "just",
    "go-task",
    "ruff",
    "yamllint",
    "shellcheck",
    "jq",
]


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

TAILSCALE = [
    "tailscale",
]

# --- Gaming ---

GAMING_PACKAGES = [
    "steam",
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
    "com.github.Matoking.protontricks",
    "net.davidotek.pupgui2",
    "com.usebottles.bottles",
    "com.heroicgameslauncher.hgl",
]


PACKAGE_REPOSITORIES = {
    "ffmpeg": "rpmfusion_free",
    "vlc-plugins-freeworld": "rpmfusion_free",
    "gstreamer1-plugins-bad-freeworld": "rpmfusion_free",
    "gstreamer1-plugins-ugly": "rpmfusion_free",
    "openh264": "fedora_cisco_openh264",
    "mozilla-openh264": "fedora_cisco_openh264",
    "librewolf": "librewolf",
    "steam": "rpmfusion_nonfree_steam",
    "nvidia-open": "nvidia_cuda",
    "codium": "vscodium",
    "hyprland": "copr_hyprland",
    "xdg-desktop-portal-hyprland": "copr_hyprland",
    "hyprshutdown": "copr_hyprland",
    "hyprlauncher": "copr_hyprland",
    "hyprsunset": "copr_hyprland",
    "hyprland-guiutils": "copr_hyprland",
    "firacode-nerd-fonts": "terra",
    "cascadiacode-nerd-fonts": "terra",
    "jetbrainsmono-nerd-fonts": "terra",
    "iosevka-nerd-fonts": "terra",
    "belleve-invis-iosevka-fonts": "terra",
    "zed": "terra",
    "zed-cli": "terra",
    "sway-audio-idle-inhibit": "terra",
    "uwsm": "terra",
}

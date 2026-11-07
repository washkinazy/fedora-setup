"""System packages, desktop environment, development tools, Tailscale, and gaming."""

import subprocess

from pyinfra.context import host
from pyinfra.facts.rpm import RpmPackages
from pyinfra.facts.server import LinuxDistribution
from pyinfra.local import include
from pyinfra.operations import files, flatpak, server, systemd

from packages.packages import (
    CONTAINER_TOOLS,
    COSMIC,
    DESKTOP_APPS,
    DEV_PACKAGES,
    FLATPAK_APPS,
    FLATPAK_CONTAINER_TOOLS,
    FLATPAK_MANAGEMENT,
    FONTS,
    GAMING_FLATPAK_APPS,
    GAMING_PACKAGES,
    GNOME,
    HYPRLAND,
    KDE,
    NIRI,
    PACKAGE_GROUPS,
    PACKAGES,
    SLACK_RPM_URL,
    TAILSCALE,
    VIRTUALIZATION,
    keyring_packages,
)
from packages.repos import install_packages


def _flatpak_remote_exists(remote):
    """Check if a Flatpak remote is configured."""
    result = subprocess.run(
        ["bash", "-c", f"flatpak remote-list --system --columns=name | grep -qx '{remote}'"],
        check=False,
    )
    return result.returncode == 0


def _flatpak_remote_enabled(remote):
    """True if a system Flatpak remote exists and is currently enabled."""
    result = subprocess.run(
        ["bash", "-c", "flatpak remotes --system --show-disabled --columns=name,options"],
        capture_output=True,
        text=True,
        check=False,
    )
    for line in result.stdout.splitlines():
        cols = line.split("\t")  # flatpak tab-separates columns when piped
        if cols[0].strip() == remote:
            options = cols[1] if len(cols) > 1 else ""
            return "disabled" not in options
    return False  # remote absent → nothing to disable


features = host.data.get("features") or {}
desktop_envs = host.data.get("desktop_environments") or {}
use_niri = desktop_envs.get("niri", False)
use_hyprland = desktop_envs.get("hyprland", False)
use_cosmic = desktop_envs.get("cosmic", False)
use_kde = desktop_envs.get("kde", False)
use_gnome = desktop_envs.get("gnome", False)


# --- Base system packages ---

install_packages(
    name="Install Fedora package groups",
    packages=PACKAGE_GROUPS,
)

install_packages(
    name="Install base system packages",
    packages=PACKAGES,
)

install_packages(
    name="Install desktop secret storage",
    packages=keyring_packages(host.get_fact(LinuxDistribution)["major"]),
)

include("modules/multimedia.py")

install_packages(
    name="Install Flatpak",
    packages=["flatpak"],
)

if not _flatpak_remote_exists("flathub"):
    server.shell(
        name="Enable Flathub repository",
        commands=[
            (
                "flatpak remote-add --if-not-exists flathub"
                " https://flathub.org/repo/flathub.flatpakrepo"
            ),
        ],
    )

if _flatpak_remote_enabled("fedora"):
    server.shell(
        name="Disable Fedora Flatpak repository",
        commands=["flatpak remote-modify --disable fedora"],
    )

polkit_rules = files.put(
    name="Deploy Flatpak polkit rules",
    src="files/49-flatpak-polkit.rules",
    dest="/etc/polkit-1/rules.d/49-flatpak-system-install.rules",
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

flatpak.packages(
    name="Install Flatpak management tools",
    packages=FLATPAK_MANAGEMENT,
    remote="flathub",
)

fonts_result = install_packages(
    name="Install system fonts",
    packages=FONTS,
)

server.shell(
    name="Rebuild font cache",
    commands=["fc-cache -f"],
    _if=[fonts_result.did_change],
)

# --- Desktop environment ---

install_packages(
    name="Install desktop applications",
    packages=DESKTOP_APPS,
)

if "slack" not in host.get_fact(RpmPackages):
    server.shell(
        name="Install Slack from official RPM",
        commands=[f"dnf install -y '{SLACK_RPM_URL}'"],
    )

flatpak.packages(
    name="Install desktop Flatpak apps",
    packages=FLATPAK_APPS,
    remote="flathub",
)

if use_niri:
    install_packages(
        name="Install Niri packages",
        packages=NIRI,
    )

if use_hyprland:
    install_packages(
        name="Install Hyprland packages",
        packages=HYPRLAND,
    )

if use_niri or use_hyprland:
    # Terra installs this unit outside systemd's standard search path.
    osd_backend_unit = files.link(
        name="Expose SwayOSD input backend unit",
        path="/etc/systemd/system/swayosd-libinput-backend.service",
        target="/usr/lib64/systemd/system/swayosd-libinput-backend.service",
    )
    systemd.daemon_reload(
        name="Reload systemd for SwayOSD input backend",
        _if=[osd_backend_unit.did_change],
    )
    systemd.service(
        name="Enable SwayOSD lock-key detection",
        service="swayosd-libinput-backend.service",
        enabled=True,
        running=True,
    )

if use_cosmic:
    install_packages(
        name="Install COSMIC desktop",
        packages=COSMIC,
    )

if use_kde:
    install_packages(
        name="Install KDE Plasma desktop",
        packages=KDE,
    )

if use_gnome:
    install_packages(
        name="Install GNOME desktop",
        packages=GNOME,
    )

# --- Development tools ---

if features.get("development"):
    install_packages(
        name="Install development packages",
        packages=DEV_PACKAGES,
    )

    install_packages(
        name="Install container tools",
        packages=CONTAINER_TOOLS,
    )

    flatpak.packages(
        name="Install Flatpak container tools",
        packages=FLATPAK_CONTAINER_TOOLS,
        remote="flathub",
    )

    install_packages(
        name="Install virtualization packages",
        packages=VIRTUALIZATION,
    )

    files.directory(
        name="Create libvirt config directory",
        path="/etc/libvirt",
        user="root",
        group="root",
        mode="0755",
    )

    files.put(
        name="Configure libvirt iptables backend",
        src="files/libvirt-network.conf",
        dest="/etc/libvirt/network.conf",
        user="root",
        group="root",
        mode="0644",
    )

    libvirt_polkit = files.put(
        name="Deploy libvirt polkit rules",
        src="files/50-libvirt-wheel.rules",
        dest="/etc/polkit-1/rules.d/50-libvirt-wheel.rules",
        user="root",
        group="root",
        mode="0644",
    )

    systemd.service(
        name="Restart polkit for libvirt rules",
        service="polkit",
        restarted=True,
        _if=[libvirt_polkit.did_change],
    )

    # libvirtd is socket-activated; do not force it to stay running.
    systemd.service(
        name="Enable libvirtd",
        service="libvirtd",
        running=None,
        enabled=True,
    )

# --- Tailscale ---

if features.get("tailscale"):
    install_packages(
        name="Install Tailscale",
        packages=TAILSCALE,
    )

# --- Gaming ---

if features.get("gaming"):
    install_packages(
        name="Install gaming packages",
        packages=GAMING_PACKAGES,
    )

    flatpak.packages(
        name="Install gaming Flatpak apps",
        packages=GAMING_FLATPAK_APPS,
        remote="flathub",
    )

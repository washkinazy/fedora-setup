"""System packages, desktop environment, development tools, Tailscale, and gaming."""

import subprocess

from pyinfra.context import host
from pyinfra.facts.server import Command
from pyinfra.operations import dnf, files, flatpak, server, systemd

from packages.packages import (
    CONTAINER_TOOLS,
    COSMIC,
    DESKTOP_APPS,
    DESKTOP_APPS_TERRA,
    DEV_PACKAGES,
    DEV_PACKAGES_VSCODIUM,
    FLATPAK_APPS,
    FLATPAK_CONTAINER_TOOLS,
    FLATPAK_MANAGEMENT,
    FONTS,
    FONTS_TERRA,
    GAMING_FLATPAK_APPS,
    GAMING_PACKAGES,
    GNOME,
    HYPRLAND,
    HYPRLAND_COPR_HYPRLAND,
    KDE,
    NIRI,
    PACKAGE_GROUPS,
    PACKAGES,
    TAILSCALE,
    VIRTUALIZATION,
    WAYLAND_WM_COMMON_TERRA,
    WAYLAND_WM_COMMON_TERRA_OR_COPR_HYPRLAND,
    with_repo_packages,
)


def _flatpak_remote_exists(remote):
    """Check if a Flatpak remote is configured."""
    result = subprocess.run(
        ["bash", "-c", f"flatpak remote-list --system --columns=name | grep -qx '{remote}'"],
        check=False,
    )
    return result.returncode == 0


def _flatpak_remote_enabled(remote):
    """True if a system Flatpak remote exists and is currently enabled.

    Reads the options column with --show-disabled so the result does not depend
    on whether the default listing hides disabled remotes (behavior has varied
    across flatpak versions); a disabled remote carries `disabled` in options.
    Gating the disable on this — rather than on mere existence — is what stops
    `remote-modify --disable` (a server.shell, so always "changed") from running
    on every deploy after the remote is already off.
    """
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
repos = host.data.get("repos") or {}
desktop_envs = host.data.get("desktop_environments") or {}
user_config = host.data.get("user_config") or {}
username = user_config.get("username", "")
use_niri = desktop_envs.get("niri", False)
use_hyprland = desktop_envs.get("hyprland", False)
use_cosmic = desktop_envs.get("cosmic", False)
use_kde = desktop_envs.get("kde", False)
use_gnome = desktop_envs.get("gnome", False)


fonts = with_repo_packages(FONTS, repos, (("terra",), FONTS_TERRA))
desktop_apps = with_repo_packages(
    DESKTOP_APPS,
    repos,
    (("terra",), DESKTOP_APPS_TERRA),
)
wayland_repo_packages = (
    ("terra", "copr_hyprland"),
    WAYLAND_WM_COMMON_TERRA_OR_COPR_HYPRLAND,
)
niri_packages = with_repo_packages(
    NIRI,
    repos,
    wayland_repo_packages,
    (("terra",), WAYLAND_WM_COMMON_TERRA),
)
hyprland_packages = with_repo_packages(
    HYPRLAND,
    repos,
    wayland_repo_packages,
    (("copr_hyprland",), HYPRLAND_COPR_HYPRLAND),
    (("terra",), WAYLAND_WM_COMMON_TERRA),
)
gaming_packages = GAMING_PACKAGES
dev_packages = with_repo_packages(
    DEV_PACKAGES,
    repos,
    (("vscodium",), DEV_PACKAGES_VSCODIUM),
)

# --- Base system packages ---

dnf.packages(
    name="Install Fedora package groups",
    packages=PACKAGE_GROUPS,
)

dnf.packages(
    name="Install base system packages",
    packages=PACKAGES,
)

# Flatpak setup
dnf.packages(
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

# Fedora's own Flatpak remote duplicates Flathub with older builds. Gated on the
# remote being currently enabled so the disable runs once and is skipped on every
# deploy thereafter (server.shell has no state check of its own).
if _flatpak_remote_enabled("fedora"):
    server.shell(
        name="Disable Fedora Flatpak repository",
        commands=["flatpak remote-modify --disable fedora"],
    )

# Enable wheel group for system Flatpak management
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

fonts_result = dnf.packages(
    name="Install system fonts",
    packages=fonts,
)

server.shell(
    name="Rebuild font cache",
    commands=["fc-cache -f"],
    _if=[fonts_result.did_change],
)

# --- Desktop environment ---

dnf.packages(
    name="Install desktop applications",
    packages=desktop_apps,
)

flatpak.packages(
    name="Install desktop Flatpak apps",
    packages=FLATPAK_APPS,
    remote="flathub",
)

# Flatpak exports Slack's desktop file and scheme declaration, but that only
# makes it an available handler. Firefox asks the OpenURI portal whether a
# default handler exists before offering its "Open Slack" prompt, so record the
# user-level default explicitly. Refresh the portal only when the association
# changes; otherwise the operation stays idempotent and does not disturb apps
# using portal sessions.
slack_desktop = "com.slack.Slack.desktop"
slack_scheme = "x-scheme-handler/slack"
slack_handler = ""
if username:
    slack_handler = host.get_fact(
        Command,
        f"xdg-mime query default {slack_scheme}",
        _sudo_user=username,
    ).strip()

if username and slack_handler != slack_desktop:
    slack_handler_result = server.shell(
        name="Register Slack URL handler",
        commands=[f"xdg-mime default {slack_desktop} {slack_scheme}"],
        _sudo_user=username,
    )

    systemd.service(
        name="Refresh desktop portal after registering Slack URL handler",
        service="xdg-desktop-portal.service",
        restarted=True,
        user_mode=True,
        user_name=username,
        _if=[slack_handler_result.did_change],
    )

# Both NIRI and HYPRLAND splat in WAYLAND_WM_COMMON and the Noctalia shell, so a
# compositor list is the whole session rather than one piece of it.
if use_niri:
    dnf.packages(
        name="Install Niri packages",
        packages=niri_packages,
    )

if use_hyprland:
    dnf.packages(
        name="Install Hyprland packages",
        packages=hyprland_packages,
    )

if use_cosmic:
    dnf.packages(
        name="Install COSMIC desktop",
        packages=COSMIC,
    )

if use_kde:
    dnf.packages(
        name="Install KDE Plasma desktop",
        packages=KDE,
    )

if use_gnome:
    dnf.packages(
        name="Install GNOME desktop",
        packages=GNOME,
    )

dnf.packages(
    name="Remove nwg-panel",
    packages=["nwg-panel"],
    present=False,
)

# --- Development tools ---

if features.get("development"):
    dnf.packages(
        name="Install development packages",
        packages=dev_packages,
    )

    dnf.packages(
        name="Install container tools",
        packages=CONTAINER_TOOLS,
    )

    flatpak.packages(
        name="Install Flatpak container tools",
        packages=FLATPAK_CONTAINER_TOOLS,
        remote="flathub",
    )

    dnf.packages(
        name="Install virtualization packages",
        packages=VIRTUALIZATION,
    )

    # Configure libvirt
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

    # Enable only (`running=None`). libvirtd is socket-activated and exits once
    # idle, so asserting running=True starts it on every deploy and the operation
    # never converges. Being enabled is the state that has to persist; the socket
    # starts the daemon on demand.
    systemd.service(
        name="Enable libvirtd",
        service="libvirtd",
        running=None,
        enabled=True,
    )

# --- Tailscale ---

if features.get("tailscale"):
    dnf.packages(
        name="Install Tailscale",
        packages=TAILSCALE,
    )

    # Install only — tailscaled is deliberately not started or enabled here.
    # `tailscale up` brings the service up and enables it on first use; managing
    # it from the deploy would fight that.
    systemd.service(
        name="Leave Tailscale service unmanaged (install only)",
        service="tailscaled",
        running=None,
        enabled=None,
    )

# --- Gaming ---

if features.get("gaming"):
    dnf.packages(
        name="Install gaming packages",
        packages=gaming_packages,
    )

    flatpak.packages(
        name="Install gaming Flatpak apps",
        packages=GAMING_FLATPAK_APPS,
        remote="flathub",
    )

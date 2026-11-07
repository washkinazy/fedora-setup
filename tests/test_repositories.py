"""Repository selection, operation ordering, and convergence without host changes."""

import runpy
import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from packages import repos
from packages.packages import (
    FLATPAK_APPS,
    GAMING_FLATPAK_APPS,
    GAMING_PACKAGES,
    NVIDIA,
    PACKAGE_REPOSITORIES,
)


class RepositorySelectionTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        context = ModuleType("pyinfra.context")
        self.installed = {}
        context.host = SimpleNamespace(name="test-host", get_fact=lambda fact: self.installed)
        rpm_facts = ModuleType("pyinfra.facts.rpm")
        rpm_facts.RpmPackages = object()
        operations = ModuleType("pyinfra.operations")
        operations.dnf = SimpleNamespace(packages=self.packages)
        operations.server = SimpleNamespace(shell=self.shell)
        self.modules = patch.dict(
            sys.modules,
            {
                "pyinfra.context": context,
                "pyinfra.operations": operations,
                "pyinfra.facts.rpm": rpm_facts,
            },
        )
        self.modules.start()
        self.addCleanup(self.modules.stop)
        repos._planned_states.clear()
        self.states = patch.object(repos, "repo_states", return_value={})
        self.read_states = self.states.start()
        self.addCleanup(self.states.stop)

    def packages(self, **kwargs):
        self.calls.append(("packages", kwargs))

    def shell(self, **kwargs):
        self.calls.append(("shell", kwargs))

    def commands(self):
        return [
            command for kind, call in self.calls if kind == "shell" for command in call["commands"]
        ]

    def test_fedora_selection_does_not_touch_repositories(self):
        repos.install_packages(
            name="Native apps", packages=["chromium", "vlc", "rawtherapee", "darktable"]
        )
        self.read_states.assert_not_called()
        self.assertEqual(len(self.calls), 1)

    def test_source_is_enabled_before_install_and_only_once(self):
        repos.install_packages(name="Development", packages=["codium"])
        self.assertIn("vscodium.repo", self.commands()[0])
        self.assertEqual(self.commands()[-1], "dnf makecache --refresh")
        self.assertEqual(self.calls[-1][1]["packages"], ["codium"])
        self.calls.clear()
        repos.install_packages(name="Development again", packages=["codium"])
        self.assertEqual(self.commands(), [])
        self.assertEqual(len(self.calls), 1)

    def test_enabled_source_converges_and_unrelated_repo_is_untouched(self):
        self.read_states.return_value = {
            "rpmfusion-nonfree-nvidia-driver": "enabled",
            "cuda-fedora44-x86_64": "disabled",
            "gitlab.com_paulcarroty_vscodium_repo": "enabled",
        }
        repos.install_packages(name="NVIDIA", packages=NVIDIA)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.commands(), [])

    def test_existing_disabled_source_is_enabled_not_registered(self):
        self.read_states.return_value = {"rpmfusion-nonfree-nvidia-driver": "disabled"}
        repos.install_packages(name="NVIDIA", packages=NVIDIA)
        self.assertEqual(
            self.commands(),
            [
                "dnf config-manager setopt rpmfusion-nonfree-nvidia-driver.enabled=1",
                "dnf makecache --refresh",
            ],
        )

    def test_nvidia_bootstraps_definition_before_drivers_and_only_once(self):
        self.read_states.return_value = {"cuda-fedora44-x86_64": "enabled"}
        repos.install_packages(name="NVIDIA", packages=NVIDIA)
        self.assertEqual(
            self.commands(),
            [
                "dnf config-manager setopt rpmfusion-nonfree-nvidia-driver.enabled=1",
                "dnf makecache --refresh",
            ],
        )
        self.assertEqual(self.calls[-1][1]["packages"], NVIDIA)
        self.assertEqual(self.calls[1][1]["packages"], ["fedora-workstation-repositories"])
        self.assertEqual(
            set(NVIDIA),
            {"xorg-x11-drv-nvidia", "akmod-nvidia-open", "xorg-x11-drv-nvidia-cuda"},
        )
        self.calls.clear()
        repos.install_packages(name="NVIDIA again", packages=NVIDIA)
        self.assertEqual(self.commands(), [])
        self.assertEqual(len(self.calls), 1)

    def test_steam_bootstraps_definition_then_enables_only_narrow_repo(self):
        repos.install_packages(name="Gaming", packages=GAMING_PACKAGES)
        self.assertEqual(self.calls[1][1]["packages"], ["fedora-workstation-repositories"])
        self.assertEqual(
            self.commands(),
            [
                "dnf config-manager setopt rpmfusion-nonfree-steam.enabled=1",
                "dnf makecache --refresh",
            ],
        )
        self.assertEqual(self.calls[-1][1]["packages"], GAMING_PACKAGES)

    def test_multimedia_replaces_free_ffmpeg_after_enabling_repos(self):
        self.installed = {"ffmpeg-free": ["8.1"]}
        runpy.run_path("modules/multimedia.py")
        commands = self.commands()
        swap = "dnf swap -y ffmpeg-free ffmpeg --allowerasing"
        self.assertLess(commands.index("dnf makecache --refresh"), commands.index(swap))
        self.assertEqual(commands[-1], swap)
        self.assertIn("vlc-plugins-freeworld", self.calls[-1][1]["packages"])
        self.assertNotIn("ffmpeg", self.calls[-1][1]["packages"])

    def test_multimedia_installs_ffmpeg_when_missing(self):
        runpy.run_path("modules/multimedia.py")
        installs = [call for kind, call in self.calls if kind == "packages"]
        ffmpeg = next(call for call in installs if call["packages"] == ["ffmpeg"])
        self.assertEqual(ffmpeg["extra_install_args"], "--allowerasing")
        self.assertFalse(any("swap" in command for command in self.commands()))

    def test_multimedia_skips_swap_and_repo_changes_on_second_run(self):
        self.installed = {"ffmpeg": ["8.1"]}
        self.read_states.return_value = {
            "rpmfusion-free": "enabled",
            "rpmfusion-free-updates": "enabled",
            "fedora-cisco-openh264": "enabled",
        }
        runpy.run_path("modules/multimedia.py")
        self.assertEqual(self.commands(), [])
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn("ffmpeg", self.calls[0][1]["packages"])

    def test_rpmfusion_enables_disabled_updates_repo(self):
        self.read_states.return_value = {
            "rpmfusion-free": "enabled",
            "rpmfusion-free-updates": "disabled",
        }
        repos.ensure_package_repositories(["ffmpeg"])
        self.assertEqual(
            self.commands()[0],
            "dnf config-manager setopt rpmfusion-free.enabled=1 rpmfusion-free-updates.enabled=1",
        )

    def test_all_sources_exist_and_native_apps_are_not_flatpaks(self):
        self.assertLessEqual(set(PACKAGE_REPOSITORIES.values()), set(repos.REPOS))
        self.assertIn("steam", GAMING_PACKAGES)
        for app in (
            "com.valvesoftware.Steam",
            "org.mozilla.firefox",
            "org.gimp.GIMP",
            "org.inkscape.Inkscape",
            "com.slack.Slack",
        ):
            self.assertNotIn(app, FLATPAK_APPS + GAMING_FLATPAK_APPS)


if __name__ == "__main__":
    unittest.main()

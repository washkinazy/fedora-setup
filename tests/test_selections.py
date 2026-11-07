"""Exercise feature selections without changing the local host."""

import runpy
import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

from packages.packages import FONTS, NVIDIA_BUILD_PACKAGES


class SelectionTests(unittest.TestCase):
    def run_module(self, path, data, *, gpu="", installed=None):
        rpm_packages = object()
        context = ModuleType("pyinfra.context")
        context.host = SimpleNamespace(
            data=data,
            get_fact=lambda fact: (installed or {}) if fact is rpm_packages else {"major": 45},
        )
        rpm = ModuleType("pyinfra.facts.rpm")
        rpm.RpmPackages = rpm_packages
        server_facts = ModuleType("pyinfra.facts.server")
        server_facts.LinuxDistribution = object()
        local = ModuleType("pyinfra.local")
        local.include = Mock()
        operations = ModuleType("pyinfra.operations")
        operations.files = Mock()
        operations.flatpak = Mock()
        operations.server = Mock()
        operations.systemd = Mock()
        operations.dnf = Mock()
        install = Mock()
        with (
            patch.dict(
                sys.modules,
                {
                    "pyinfra.context": context,
                    "pyinfra.facts.rpm": rpm,
                    "pyinfra.facts.server": server_facts,
                    "pyinfra.local": local,
                    "pyinfra.operations": operations,
                },
            ),
            patch("packages.repos.install_packages", install),
            patch(
                "subprocess.run",
                return_value=SimpleNamespace(
                    returncode=0,
                    stdout=gpu,
                ),
            ),
        ):
            runpy.run_path(path)
        return install, operations

    def test_development_controls_editors_but_not_fonts(self):
        for enabled in (False, True):
            with self.subTest(development=enabled):
                install, operations = self.run_module(
                    "modules/packages.py",
                    {"features": {"development": enabled}},
                    installed={"slack": ["4.53.276"]},
                )
                packages = [p for call in install.call_args_list for p in call.kwargs["packages"]]
                for editor in ("zed", "zed-cli", "codium"):
                    self.assertEqual(editor in packages, enabled)
                self.assertTrue(set(FONTS).issubset(packages))
                self.assertFalse(
                    any(
                        "Slack" in call.kwargs.get("name", "")
                        for call in operations.server.shell.call_args_list
                    )
                )

    def test_network_mount_list_enables_cifs_without_feature_flag(self):
        for mounts in ([], [{"name": "media", "where": "/synology/media", "what": "//nas/media"}]):
            with self.subTest(mounts=mounts):
                _, operations = self.run_module("modules/storage.py", {"storage_mounts": mounts})
                self.assertEqual(operations.dnf.packages.call_count, int(bool(mounts)))
                self.assertEqual(operations.files.template.call_count, 2 * len(mounts))

    def test_kernel_build_tools_follow_nvidia_hardware(self):
        for vendor in ("Intel", "NVIDIA"):
            with self.subTest(vendor=vendor):
                install, _ = self.run_module(
                    "modules/hardware.py",
                    {},
                    gpu=f"01:00.0 VGA compatible controller: {vendor}",
                )
                packages = [p for call in install.call_args_list for p in call.kwargs["packages"]]
                self.assertEqual(set(NVIDIA_BUILD_PACKAGES).issubset(packages), vendor == "NVIDIA")

"""Release normalization ordering and convergence without host changes."""

import runpy
import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch


class ReleaseTests(unittest.TestCase):
    def run_init(self, provider, identity="basic"):
        rpm_fact = object()
        command_fact = object()
        context = ModuleType("pyinfra.context")
        installed = {f"fedora-release-identity-{identity}": ["44"]} if identity else {}
        context.host = SimpleNamespace(
            get_fact=lambda fact, **kwargs: installed if fact is rpm_fact else provider
        )
        rpm = ModuleType("pyinfra.facts.rpm")
        rpm.RpmPackages = rpm_fact
        server = ModuleType("pyinfra.facts.server")
        server.Command = command_fact
        operations = ModuleType("pyinfra.operations")
        calls = Mock()
        operations.server = SimpleNamespace(shell=calls.shell)
        operations.dnf = SimpleNamespace(packages=calls.packages)
        with patch.dict(
            sys.modules,
            {
                "pyinfra.context": context,
                "pyinfra.facts.rpm": rpm,
                "pyinfra.facts.server": server,
                "pyinfra.operations": operations,
            },
        ):
            runpy.run_path("modules/init.py")
        return calls

    def test_variant_swaps_after_identity(self):
        for variant in ("cosmic", "workstation", "kde-desktop"):
            with self.subTest(variant=variant):
                calls = self.run_init(f"fedora-release-{variant}", variant)
                self.assertEqual(
                    [call.kwargs["commands"] for call in calls.shell.call_args_list],
                    [
                        [
                            f"dnf swap -y fedora-release-identity-{variant} "
                            "fedora-release-identity-basic"
                        ],
                        [f"dnf swap -y fedora-release-{variant} fedora-release"],
                    ],
                )

    def test_basic_identity_with_variant_still_swaps_release(self):
        calls = self.run_init("fedora-release-cosmic")
        self.assertEqual(calls.shell.call_count, 1)
        self.assertEqual(
            calls.shell.call_args.kwargs["commands"],
            ["dnf swap -y fedora-release-cosmic fedora-release"],
        )

    def test_generic_second_run_has_no_operations(self):
        self.assertEqual(self.run_init("fedora-release").mock_calls, [])

    def test_missing_identity_installed_before_release_swap(self):
        calls = self.run_init("fedora-release-cosmic", identity=None)
        self.assertEqual([call[0] for call in calls.mock_calls], ["packages", "shell"])

    def test_ambiguous_or_missing_provider_fails(self):
        for provider in ("", "fedora-release\nfedora-release-cosmic"):
            with self.subTest(provider=provider), self.assertRaises(SystemExit):
                self.run_init(provider)

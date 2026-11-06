"""Check persistent source restrictions using DNF5's configuration loader."""

import fnmatch
import subprocess
import tempfile
import unittest
from pathlib import Path

from packages.repo_policy import other_repository_patterns, render_policy

try:
    import libdnf5
except ImportError:
    libdnf5 = None


class RepositoryPolicyTests(unittest.TestCase):
    def test_binding_patterns_allow_only_designated_repositories(self):
        allowed = ["example", "example-updates"]
        patterns = list(other_repository_patterns(allowed))
        for rid in allowed:
            self.assertFalse(any(fnmatch.fnmatchcase(rid, pattern) for pattern in patterns))
        for rid in ("e", "exampl", "example-", "example-testing", "example-updates-extra", "other"):
            self.assertTrue(any(fnmatch.fnmatchcase(rid, pattern) for pattern in patterns), rid)

    @unittest.skipIf(libdnf5 is None, "Fedora's python3-libdnf5 is required")
    def test_dnf_loads_weights_and_bindings_without_clearing_existing_excludes(self):
        expected = {
            "fedora": (10, {"steam", "codium"}),
            "updates": (10, {"steam", "codium"}),
            "rpmfusion-free-updates": (20, {"steam", "codium"}),
            "fedora-cisco-openh264": (20, {"steam", "codium"}),
            "rpmfusion-nonfree-steam": (20, {"codium"}),
            "gitlab.com_paulcarroty_vscodium_repo": (30, {"steam"}),
            "cuda-fedora44-x86_64": (30, {"steam", "codium"}),
            "copr:copr.fedorainfracloud.org:lionheartp:Hyprland": (40, {"steam", "codium"}),
            "terra": (50, {"steam", "codium"}),
            "new-unmanaged-repo": (99, {"steam", "codium"}),
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repos = root / "etc/yum.repos.d"
            repos.mkdir(parents=True)
            (repos / "test.repo").write_text(
                "".join(
                    f"[{rid}]\nbaseurl=file:///unused\nenabled=0\nexcludepkgs=keep-me\n"
                    for rid in expected
                )
            )
            overrides = root / "etc/dnf/repos.override.d"
            overrides.mkdir(parents=True)
            (overrides / "99-zz-fedora-setup.repo").write_text(render_policy())
            for _ in range(2):
                base = libdnf5.base.Base()
                base.get_config().installroot = temporary
                base.get_config().get_plugins_option().set(False)
                base.setup()
                base.get_repo_sack().create_repos_from_system_configuration()
                found = set()
                for repo in libdnf5.repo.RepoQuery(base):
                    found.add(repo.get_id())
                    priority, excluded = expected[repo.get_id()]
                    config = repo.get_config()
                    self.assertEqual(config.get_priority_option().get_value(), priority)
                    self.assertEqual(
                        set(config.get_excludepkgs_option().get_value()), excluded | {"keep-me"}
                    )
                    self.assertFalse(config.get_enabled_option().get_value())
                self.assertEqual(found, set(expected))

    def test_setup_policy_precedes_tool_bootstrap_and_upgrade(self):
        script = """
source ./setup.sh
check_fedora() { :; }
require_inventory() { :; }
start_sudo_keepalive() { :; }
stop_sudo_keepalive() { :; }
configure_repository_policy() { echo policy; }
ensure_tooling() { echo tooling; }
update_system() { echo upgrade; }
run_pyinfra() { echo deploy; }
main "$@"
"""
        for arguments, expected in (
            ([], ["policy", "tooling", "upgrade", "deploy"]),
            (["--skip-update"], ["policy", "tooling", "deploy"]),
            (["--dry-run"], ["tooling", "deploy"]),
        ):
            result = subprocess.run(
                ["bash", "-c", script, "test", *arguments],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(result.stdout.splitlines(), expected)

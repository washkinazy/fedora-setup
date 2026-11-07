"""Bootstrap regressions without installing tools or deploying the host."""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SetupToolingTests(unittest.TestCase):
    def run_shell(self, body):
        return subprocess.run(
            ["bash", "-c", "source ./setup.sh\n" + body],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_working_tool_is_reused(self):
        result = self.run_shell("""
find_pyinfra() { echo fake_pyinfra; }
fake_pyinfra() { echo 'pyinfra: v3.10'; }
uv() { echo 'unexpected install'; return 1; }
ensure_tooling false
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("unexpected install", result.stdout)

    def test_dry_run_rejects_broken_tool_without_repair(self):
        result = self.run_shell("""
find_pyinfra() { echo fake_pyinfra; }
fake_pyinfra() { echo 'ModuleNotFoundError' >&2; return 1; }
uv() { echo 'unexpected install'; return 1; }
ensure_tooling true
""")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("working pyinfra is required", result.stderr)
        self.assertNotIn("unexpected install", result.stdout)

    def test_broken_tool_is_repaired_and_verified(self):
        result = self.run_shell("""
repaired=false
find_pyinfra() { echo fake_pyinfra; }
fake_pyinfra() { [[ "$repaired" == true ]] && echo 'pyinfra: v3.10'; }
uv() {
    printf '%s\\n' "$*"
    if [[ "$1 $2" == 'tool install' ]]; then repaired=true; fi
}
ensure_tooling false
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("python install 3.14", result.stdout)
        self.assertIn("--managed-python --force --reinstall", result.stdout)
        self.assertIn("pyinfra ready", result.stderr)

    def test_still_broken_tool_stops_setup(self):
        result = self.run_shell("""
find_pyinfra() { echo fake_pyinfra; }
fake_pyinfra() { return 1; }
uv() { return 0; }
ensure_tooling false
""")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("still unusable", result.stderr)

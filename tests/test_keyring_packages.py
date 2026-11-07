"""Release-specific secret storage selection."""

import unittest

from packages.packages import HYPRLAND, NIRI, keyring_packages


class KeyringPackagesTests(unittest.TestCase):
    def test_fedora_44_uses_available_gnome_backend(self):
        self.assertEqual(keyring_packages(44), ["gnome-keyring", "gnome-keyring-pam"])

    def test_fedora_45_uses_oo7_without_obsoleted_gnome_packages(self):
        self.assertEqual(keyring_packages(45), ["oo7-daemon", "oo7-portal", "pam_oo7"])

    def test_unknown_release_fails(self):
        with self.assertRaises(ValueError):
            keyring_packages(None)

    def test_compositors_select_one_shared_agent(self):
        for packages in (NIRI, HYPRLAND):
            self.assertEqual(packages.count("mate-polkit"), 1)
            for old in ("polkit-kde", "hyprpolkitagent", "kf6-kwallet", "pam-kwallet"):
                self.assertNotIn(old, packages)

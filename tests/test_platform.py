import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dev"))
import iconik_locator as loc


class PlatformTests(unittest.TestCase):
    def test_windows_config_uses_appdata(self):
        with patch.object(sys, "platform", "win32"), patch.dict(os.environ, {"APPDATA": "/user/appdata"}):
            self.assertEqual(loc.config_directory(), "/user/appdata/IconikLocator")

    def test_linux_config_uses_xdg(self):
        with patch.object(sys, "platform", "linux"), patch.dict(os.environ, {"XDG_CONFIG_HOME": "/user/config"}):
            self.assertEqual(loc.config_directory(), "/user/config/IconikLocator")

    def test_mac_config_stays_compatible(self):
        with patch.object(sys, "platform", "darwin"):
            self.assertTrue(loc.config_directory().endswith("Library/Application Support/IconikLocator"))

    def test_native_credentials_use_secure_backend(self):
        for platform in ("win32", "linux"):
            backend = Mock(priority=1)
            backend.get_password.return_value = "test-token"
            with self.subTest(platform=platform), patch.object(sys, "platform", platform), patch.object(loc.KeychainStore, "_backend", return_value=backend):
                loc.KeychainStore.set("auth_token", "test-token")
                self.assertEqual(loc.KeychainStore.get("auth_token"), "test-token")
                backend.set_password.assert_called_once_with("IconikLocator", "auth_token", "test-token")
                loc.KeychainStore.delete("auth_token")
                backend.delete_password.assert_called_once_with("IconikLocator", "auth_token")

    def test_unavailable_keyring_does_not_write_plaintext(self):
        with patch.object(sys, "platform", "linux"), patch.object(loc.KeychainStore, "_backend", side_effect=RuntimeError("locked")), patch.object(loc.ConfigStore, "save") as save:
            self.assertEqual(loc.KeychainStore.get("auth_token"), "")
            with self.assertRaisesRegex(RuntimeError, "Credentials were not saved"):
                loc.KeychainStore.set("auth_token", "test-token")
            save.assert_not_called()

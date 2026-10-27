import os
import unittest
from pathlib import Path
from unittest.mock import patch

from cc_usage_display.config import default_cc_switch_exe


class DefaultCcSwitchPathTests(unittest.TestCase):
    def test_finds_system_mac_app(self):
        with (
            patch("cc_usage_display.config.Path.exists", return_value=True),
            patch("cc_usage_display.config.sys.platform", "darwin"),
        ):
            expected = str(Path("/Applications/CC Switch.app"))
            self.assertEqual(default_cc_switch_exe(), expected)

    def test_finds_user_mac_app(self):
        with (
            patch("cc_usage_display.config.Path.exists", side_effect=[False, True]),
            patch("cc_usage_display.config.Path.home", return_value=Path("/Users/test")),
            patch("cc_usage_display.config.sys.platform", "darwin"),
        ):
            expected = str(Path.home() / "Applications" / "CC Switch.app")
            self.assertEqual(default_cc_switch_exe(), expected)

    def test_preserves_windows_app_lookup(self):
        with (
            patch("cc_usage_display.config.Path.exists", return_value=True),
            patch.dict(os.environ, {"LOCALAPPDATA": r"C:\Users\test\AppData\Local"}),
            patch("cc_usage_display.config.sys.platform", "win32"),
        ):
            expected = str(
                Path(os.environ["LOCALAPPDATA"])
                / "Programs"
                / "CC Switch"
                / "cc-switch.exe"
            )
            self.assertEqual(default_cc_switch_exe(), expected)


if __name__ == "__main__":
    unittest.main()

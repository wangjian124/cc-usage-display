import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cc_usage_display.server import focus_cc_switch


class FocusCcSwitchTests(unittest.TestCase):
    @patch("cc_usage_display.server.subprocess.run")
    @patch("cc_usage_display.server.sys.platform", "darwin")
    def test_opens_cc_switch_on_macos(self, run):
        self.assertTrue(focus_cc_switch(None))
        run.assert_called_once_with(
            ["open", "-a", "CC Switch"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @patch("cc_usage_display.server.subprocess.run")
    @patch("cc_usage_display.server.sys.platform", "darwin")
    def test_returns_false_when_open_fails_on_macos(self, run):
        run.side_effect = subprocess.CalledProcessError(1, ["open"])

        self.assertFalse(focus_cc_switch(None))

    @patch("cc_usage_display.server.subprocess.run")
    @patch("cc_usage_display.server.sys.platform", "darwin")
    def test_uses_existing_app_bundle(self, run):
        with tempfile.TemporaryDirectory() as app_dir:
            focus_cc_switch(app_dir)

        self.assertEqual(run.call_args.args[0], ["open", "-a", app_dir])

    @patch("cc_usage_display.server.subprocess.run")
    @patch("cc_usage_display.server.sys.platform", "darwin")
    def test_ignores_stale_app_path(self, run):
        self.assertTrue(focus_cc_switch("/Applications/Missing.app"))

        self.assertEqual(run.call_args.args[0], ["open", "-a", "CC Switch"])

    @patch("cc_usage_display.server.sys.platform", "linux")
    def test_unsupported_platform_returns_false(self):
        self.assertFalse(focus_cc_switch(None))


if __name__ == "__main__":
    unittest.main()

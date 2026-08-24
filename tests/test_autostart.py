"""
Tests for awall.autostart
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from awall.autostart import disable_autostart, enable_autostart, is_autostart_enabled


class TestAutostart(unittest.TestCase):
    def test_autostart_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            autostart_file = Path(tmpdir) / "awall-tray.desktop"
            with patch("awall.autostart.get_autostart_file", return_value=autostart_file), \
                 patch("awall.autostart.get_autostart_dir", return_value=Path(tmpdir)):

                self.assertFalse(is_autostart_enabled())
                self.assertTrue(enable_autostart())
                self.assertTrue(autostart_file.exists())
                self.assertTrue(is_autostart_enabled())

                self.assertTrue(disable_autostart())
                self.assertFalse(autostart_file.exists())
                self.assertFalse(is_autostart_enabled())


if __name__ == "__main__":
    unittest.main()

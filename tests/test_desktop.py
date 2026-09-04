"""
Tests for awall.desktop module (desktop launcher, icons, and menus).
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from awall.desktop import (
    generate_desktop_entry_content,
    get_desktop_app_status,
    install_desktop_app,
    is_desktop_app_installed,
    uninstall_desktop_app,
)


class TestDesktop(unittest.TestCase):
    def test_desktop_entry_generation(self):
        content = generate_desktop_entry_content()
        self.assertIn("[Desktop Entry]", content)
        self.assertIn("Type=Application", content)
        self.assertIn("Name=AuraWall Wallpaper Engine", content)
        self.assertIn("Icon=aurawall", content)
        self.assertIn("Actions=Next;Prev;Tray;Settings;Pause;Resume;", content)

    def test_desktop_app_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir) / "applications"
            app_dir.mkdir(parents=True, exist_ok=True)
            desktop_file = app_dir / "io.github.aurawall.desktop"
            icons_dir = Path(tmpdir) / "icons" / "hicolor"
            pixmaps_dir = Path(tmpdir) / "pixmaps"

            with patch("awall.desktop.get_applications_dir", return_value=app_dir), \
                 patch("awall.desktop.get_desktop_file", return_value=desktop_file), \
                 patch("awall.desktop.get_icons_base_dir", return_value=icons_dir), \
                 patch("awall.desktop.get_pixmaps_dir", return_value=pixmaps_dir):

                self.assertFalse(is_desktop_app_installed())
                self.assertTrue(install_desktop_app())
                self.assertTrue(desktop_file.exists())
                self.assertTrue(is_desktop_app_installed())

                status = get_desktop_app_status()
                self.assertTrue(status["installed"])
                self.assertEqual(status["file"], str(desktop_file))

                self.assertTrue(uninstall_desktop_app())
                self.assertFalse(desktop_file.exists())
                self.assertFalse(is_desktop_app_installed())


if __name__ == "__main__":
    unittest.main()

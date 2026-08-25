"""
Unit tests for lock screen wallpaper synchronization and visual effect processing.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from awall.lockscreen import (
    apply_to_lock_screen,
    detect_lock_screen_backend,
    process_lock_wallpaper,
    sync_lock_screen,
)


class TestLockScreen(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.target_dir = Path(self.tmp_dir.name)
        # Create a dummy image
        self.test_img = self.target_dir / "test_wallpaper.jpg"
        img = Image.new("RGB", (100, 100), color=(120, 180, 240))
        img.save(self.test_img, format="JPEG")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_detect_lock_backend(self):
        with patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "GNOME"}):
            with patch("shutil.which", side_effect=lambda x: "/usr/bin/gsettings" if x == "gsettings" else None):
                self.assertEqual(detect_lock_screen_backend(), "gnome")

        with patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "KDE"}):
            with patch("shutil.which", side_effect=lambda x: "/usr/bin/kwriteconfig6" if x == "kwriteconfig6" else None):
                self.assertEqual(detect_lock_screen_backend(), "kde")

        with patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "XFCE"}):
            with patch("shutil.which", side_effect=lambda x: "/usr/bin/xfce4-screensaver-command" if x == "xfce4-screensaver-command" else None):
                self.assertEqual(detect_lock_screen_backend(), "xfce")

    def test_process_lock_wallpaper_none(self):
        out = process_lock_wallpaper(
            image_path=self.test_img,
            effect="none",
            output_dir=self.target_dir,
        )
        self.assertTrue(out.exists())
        self.assertEqual(out.name, "lockscreen.png")

    def test_process_lock_wallpaper_blur(self):
        out = process_lock_wallpaper(
            image_path=self.test_img,
            effect="blur",
            blur_radius=10,
            output_dir=self.target_dir,
        )
        self.assertTrue(out.exists())
        with Image.open(out) as res:
            self.assertEqual(res.size, (100, 100))

    def test_process_lock_wallpaper_dim(self):
        out = process_lock_wallpaper(
            image_path=self.test_img,
            effect="dim",
            dim_opacity=0.5,
            output_dir=self.target_dir,
        )
        self.assertTrue(out.exists())
        with Image.open(out) as res:
            self.assertEqual(res.size, (100, 100))

    def test_process_lock_wallpaper_blur_dim(self):
        out = process_lock_wallpaper(
            image_path=self.test_img,
            effect="blur_dim",
            blur_radius=5,
            dim_opacity=0.3,
            output_dir=self.target_dir,
        )
        self.assertTrue(out.exists())
        with Image.open(out) as res:
            self.assertEqual(res.size, (100, 100))

    @patch("subprocess.run")
    def test_apply_to_lock_screen(self, mock_run):
        ok = apply_to_lock_screen(self.test_img, backend="gnome")
        self.assertTrue(ok)
        mock_run.assert_called()

    @patch("awall.lockscreen.apply_to_lock_screen", return_value=True)
    def test_sync_lock_screen_enabled(self, mock_apply):
        config = {
            "display": {
                "lock_screen": {
                    "enabled": True,
                    "effect": "blur",
                    "blur_radius": 12,
                    "dim_opacity": 0.4,
                }
            }
        }
        with patch("awall.lockscreen.get_cache_dir", return_value=self.target_dir):
            ok = sync_lock_screen(self.test_img, config=config)
            self.assertTrue(ok)
            mock_apply.assert_called_once()

    def test_sync_lock_screen_disabled(self):
        config = {
            "display": {
                "lock_screen": {
                    "enabled": False,
                }
            }
        }
        ok = sync_lock_screen(self.test_img, config=config)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()

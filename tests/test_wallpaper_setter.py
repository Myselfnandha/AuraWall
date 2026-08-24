"""
Tests for awall.wallpaper_setter
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image

from awall.wallpaper_setter import ALL_BACKENDS, detect_backend, set_wallpaper


class TestWallpaperSetter(unittest.TestCase):
    def test_backends_list(self):
        backend_names = [b.name for b in ALL_BACKENDS]
        self.assertIn("xfdesktop", backend_names)
        self.assertIn("gsettings", backend_names)
        self.assertIn("plasma", backend_names)
        self.assertIn("feh", backend_names)
        self.assertIn("swaybg", backend_names)
        self.assertIn("hyprpaper", backend_names)
        self.assertIn("swww", backend_names)

    def test_detect_backend_override(self):
        backend = detect_backend("feh")
        self.assertIsNotNone(backend)
        self.assertEqual(backend.name, "feh")

    def test_set_wallpaper_nonexistent_file(self):
        with self.assertRaises(FileNotFoundError):
            set_wallpaper("/tmp/non_existent_wallpaper_file.jpg")

    def test_set_wallpaper_mocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = Path(tmpdir) / "test.jpg"
            img = Image.new("RGB", (100, 100), color="red")
            img.save(img_path, "JPEG")

            with patch("awall.wallpaper_setter.detect_backend") as mock_detect:
                mock_backend = MagicMock()
                mock_backend.name = "mock_backend"
                mock_backend.set_wallpaper.return_value = True
                mock_detect.return_value = mock_backend

                res = set_wallpaper(img_path)
                self.assertTrue(res)
                mock_backend.set_wallpaper.assert_called_once()


if __name__ == "__main__":
    unittest.main()

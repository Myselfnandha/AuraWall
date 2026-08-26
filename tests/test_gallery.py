"""
Unit tests for visual Gallery and thumbnail caching engine.
"""

import tempfile
import unittest
from pathlib import Path
from PIL import Image

from awall.cache import CacheManager
from awall.history import HistoryManager


class TestGallery(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.tmp_dir.name)
        self.history_mgr = HistoryManager(history_file=self.cache_dir / "history.json")
        self.cache_mgr = CacheManager(cache_dir=self.cache_dir, history_mgr=self.history_mgr)

        # Create a test high-res image
        self.test_img = self.cache_dir / "test_wallpaper.jpg"
        img = Image.new("RGB", (3840, 2160), color=(120, 80, 200))
        img.save(self.test_img, "JPEG")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_thumbnail_generation(self):
        thumb_path = self.cache_mgr.get_thumbnail(self.test_img, width=320, height=180)
        self.assertTrue(thumb_path.exists())
        self.assertIn("thumbnails", str(thumb_path))

        with Image.open(thumb_path) as thumb_img:
            w, h = thumb_img.size
            self.assertLessEqual(w, 320)
            self.assertLessEqual(h, 180)

    def test_thumbnail_cache_reuse(self):
        # First call generates thumbnail
        t1 = self.cache_mgr.get_thumbnail(self.test_img, width=320, height=180)
        mtime1 = t1.stat().st_mtime

        # Second call returns existing cached file without re-saving
        t2 = self.cache_mgr.get_thumbnail(self.test_img, width=320, height=180)
        self.assertEqual(t1, t2)
        self.assertEqual(mtime1, t2.stat().st_mtime)

    def test_thumbnail_nonexistent_file(self):
        non_existent = self.cache_dir / "missing.jpg"
        res = self.cache_mgr.get_thumbnail(non_existent)
        self.assertEqual(res, non_existent)


if __name__ == "__main__":
    unittest.main()

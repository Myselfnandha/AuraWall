"""
Tests for awall.cache
"""

import tempfile
import time
import unittest
from pathlib import Path
from PIL import Image

from awall.cache import CacheManager
from awall.history import HistoryManager


class TestCache(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.tmpdir.name) / "cache"
        self.history_file = Path(self.tmpdir.name) / "history.json"
        self.history_mgr = HistoryManager(self.history_file)
        self.mgr = CacheManager(cache_dir=self.cache_dir, max_wallpapers=3, history_mgr=self.history_mgr)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _create_dummy_image(self, filename: str) -> Path:
        p = self.cache_dir / filename
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(p, "JPEG")
        return p

    def test_cache_files_and_stats(self):
        self._create_dummy_image("img_1.jpg")
        self._create_dummy_image("img_2.jpg")
        files = self.mgr.get_cached_files()
        self.assertEqual(len(files), 2)

        count, mb = self.mgr.get_stats()
        self.assertEqual(count, 2)
        self.assertGreater(mb, 0.0)

    def test_cache_pruning(self):
        # Create 5 images when max is 3
        for i in range(5):
            p = self._create_dummy_image(f"img_{i}.jpg")
            time.sleep(0.01)

        self.assertEqual(len(self.mgr.get_cached_files()), 5)
        deleted = self.mgr.prune()
        self.assertEqual(deleted, 2)
        self.assertEqual(len(self.mgr.get_cached_files()), 3)

    def test_offline_wallpaper_fallback(self):
        p1 = self._create_dummy_image("wall_a.jpg")
        p2 = self._create_dummy_image("wall_b.jpg")

        chosen = self.mgr.get_offline_wallpaper(exclude_path=str(p1))
        self.assertEqual(chosen, p2)


if __name__ == "__main__":
    unittest.main()

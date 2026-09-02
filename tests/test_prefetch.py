"""
Tests for awall.prefetch PrefetchManager
"""

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image

from awall.config import get_default_config
from awall.daemon import change_wallpaper
from awall.prefetch import PrefetchManager


class TestPrefetch(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.tmpdir.name)
        self.mgr = PrefetchManager(cache_dir=self.cache_dir)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_get_prefetched_empty(self):
        self.assertIsNone(self.mgr.get_prefetched())

    def test_pop_prefetched(self):
        img_file = self.cache_dir / "test_wall.jpg"
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(img_file, "JPEG")

        # Simulate existing prefetch payload
        meta = {
            "file_path": str(img_file),
            "photographer": "Fast Photographer",
            "photographer_url": "https://example.com/p",
            "source_name": "bing",
            "url": "https://example.com/test.jpg",
            "topic": "nature",
            "timestamp": time.time(),
        }
        self.mgr.meta_file.write_text(json.dumps(meta), encoding="utf-8")

        got = self.mgr.get_prefetched()
        self.assertIsNotNone(got)
        self.assertEqual(got["photographer"], "Fast Photographer")

        popped = self.mgr.pop_prefetched()
        self.assertIsNotNone(popped)
        self.assertEqual(popped["file_path"], str(img_file))

        # After popping, meta file should be cleared
        self.assertFalse(self.mgr.meta_file.exists())

    @patch("awall.daemon.set_wallpaper")
    def test_instant_rotation_with_prefetch(self, mock_set_wall):
        mock_set_wall.return_value = True

        img_file = self.cache_dir / "test_fast_wall.jpg"
        img = Image.new("RGB", (100, 100), color="purple")
        img.save(img_file, "JPEG")

        # Store in prefetch buffer
        meta = {
            "file_path": str(img_file),
            "photographer": "Instant Artist",
            "photographer_url": "https://example.com/artist",
            "source_name": "wallhaven",
            "url": "https://example.com/fast.jpg",
            "topic": "space",
            "timestamp": time.time(),
        }

        with patch("awall.prefetch.PrefetchManager.get_default", return_value=self.mgr):
            self.mgr.meta_file.write_text(json.dumps(meta), encoding="utf-8")

            config = get_default_config()
            config["cache"]["directory"] = str(self.cache_dir)
            success = change_wallpaper(config=config, ignore_pause=True)
            self.assertTrue(success)
            mock_set_wall.assert_called_once()

    def test_multi_slot_queue(self):
        # Add 3 items to queue
        items = []
        for i in range(3):
            f = self.cache_dir / f"wall_{i}.jpg"
            img = Image.new("RGB", (50, 50), color="red")
            img.save(f, "JPEG")
            items.append({
                "file_path": str(f),
                "photographer": f"Artist {i}",
                "url": f"https://example.com/{i}.jpg",
                "source_name": "bing",
                "topic": "nature",
                "timestamp": time.time(),
            })

        self.mgr._write_queue(items)
        self.assertEqual(self.mgr.get_queue_length(), 3)

        p1 = self.mgr.pop_prefetched()
        self.assertEqual(p1["photographer"], "Artist 0")
        self.assertEqual(self.mgr.get_queue_length(), 2)

        p2 = self.mgr.pop_prefetched()
        self.assertEqual(p2["photographer"], "Artist 1")
        self.assertEqual(self.mgr.get_queue_length(), 1)

    def test_instant_fallback(self):
        f = self.cache_dir / "cached_fallback.jpg"
        img = Image.new("RGB", (50, 50), color="green")
        img.save(f, "JPEG")

        fallback = self.mgr.get_instant_fallback()
        self.assertIsNotNone(fallback)
        self.assertEqual(fallback["source_name"], "cache")


if __name__ == "__main__":
    unittest.main()

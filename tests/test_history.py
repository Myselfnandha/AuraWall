"""
Tests for awall.history
"""

import tempfile
import unittest
from pathlib import Path

from awall.history import HistoryManager


class TestHistory(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.history_file = Path(self.tmpdir.name) / "history.json"
        self.mgr = HistoryManager(self.history_file)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_add_and_get_entry(self):
        entry = self.mgr.add_entry(
            source="unsplash",
            file_path="/tmp/fake_wall.jpg",
            url="https://images.unsplash.com/test",
            photographer="John Doe",
            topic="nature",
        )
        self.assertEqual(entry["source"], "unsplash")
        self.assertEqual(entry["photographer"], "John Doe")
        self.assertFalse(entry["is_favorite"])

        current = self.mgr.get_current()
        self.assertIsNotNone(current)
        self.assertEqual(current["id"], entry["id"])

    def test_favorites(self):
        entry1 = self.mgr.add_entry(source="unsplash", file_path="/tmp/wall1.jpg", photographer="Artist 1")
        entry2 = self.mgr.add_entry(source="pexels", file_path="/tmp/wall2.jpg", photographer="Artist 2")

        # Mark entry 2 as favorite
        updated = self.mgr.mark_favorite(file_path_or_id=entry2["id"], is_fav=True)
        self.assertTrue(updated["is_favorite"])

        favs = self.mgr.get_favorites()
        self.assertEqual(len(favs), 1)
        self.assertEqual(favs[0]["id"], entry2["id"])

        # Check is_file_favorite
        self.assertTrue(self.mgr.is_file_favorite("/tmp/wall2.jpg"))
        self.assertFalse(self.mgr.is_file_favorite("/tmp/wall1.jpg"))

        # Unmark
        self.mgr.mark_favorite(file_path_or_id=entry2["id"], is_fav=False)
        self.assertEqual(len(self.mgr.get_favorites()), 0)


if __name__ == "__main__":
    unittest.main()

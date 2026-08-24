"""
Tests for awall.sources
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image

from awall.config import get_default_config
from awall.sources import ALL_SOURCES, fetch_wallpaper_from_chain, get_source, pick_next_topic
from awall.sources.local import LocalSource
from awall.sources.unsplash import UnsplashSource


class TestSources(unittest.TestCase):
    def test_sources_registry(self):
        self.assertIn("unsplash", ALL_SOURCES)
        self.assertIn("pexels", ALL_SOURCES)
        self.assertIn("pixabay", ALL_SOURCES)
        self.assertIn("reddit", ALL_SOURCES)
        self.assertIn("local", ALL_SOURCES)

        self.assertIsNotNone(get_source("unsplash"))
        self.assertIsNone(get_source("nonexistent"))

    def test_pick_next_topic(self):
        config = get_default_config()
        config["topics"]["enabled"] = ["nature", "space"]
        config["topics"]["mode"] = "sequential"
        config["topics"]["current_index"] = 0

        t1 = pick_next_topic(config)
        self.assertEqual(t1, "nature")
        t2 = pick_next_topic(config)
        self.assertEqual(t2, "space")
        t3 = pick_next_topic(config)
        self.assertEqual(t3, "nature")

    def test_local_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = Path(tmpdir) / "test_local.png"
            img = Image.new("RGB", (200, 200), color="green")
            img.save(img_path, "PNG")

            config = get_default_config()
            config["sources"]["local"]["paths"] = [tmpdir]

            local_src = LocalSource()
            info = local_src.fetch("nature", {}, config)
            self.assertEqual(info.source_name, "local")
            self.assertEqual(info.local_path, str(img_path))
            self.assertEqual(info.width, 200)

    @patch("requests.get")
    def test_unsplash_fetch_mock(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "user": {"name": "Test Photographer", "links": {"html": "https://test.com"}},
                    "urls": {"raw": "https://images.unsplash.com/test_url"},
                    "width": 3840,
                    "height": 2160,
                    "alt_description": "Beautiful test landscape",
                }
            ]
        }
        mock_get.return_value = mock_response

        src = UnsplashSource()
        config = get_default_config()
        info = src.fetch("nature", {"orientation": "landscape"}, config)

        self.assertEqual(info.source_name, "unsplash")
        self.assertEqual(info.photographer, "Test Photographer")
        self.assertIn("https://images.unsplash.com/test_url", info.url)


if __name__ == "__main__":
    unittest.main()

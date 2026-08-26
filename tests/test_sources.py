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
from awall.sources.bing import BingSource
from awall.sources.local import LocalSource
from awall.sources.unsplash import UnsplashSource
from awall.sources.wallhaven import WallhavenSource


class TestSources(unittest.TestCase):
    def test_sources_registry(self):
        self.assertIn("wallhaven", ALL_SOURCES)
        self.assertIn("bing", ALL_SOURCES)
        self.assertIn("unsplash", ALL_SOURCES)
        self.assertIn("pexels", ALL_SOURCES)
        self.assertIn("pixabay", ALL_SOURCES)
        self.assertIn("reddit", ALL_SOURCES)
        self.assertIn("local", ALL_SOURCES)

        self.assertIsNotNone(get_source("wallhaven"))
        self.assertIsNotNone(get_source("bing"))
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

    @patch("requests.get")
    def test_wallhaven_fetch_mock(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "abc123",
                    "path": "https://w.wallhaven.cc/full/ab/wallhaven-abc123.jpg",
                    "url": "https://wallhaven.cc/w/abc123",
                    "dimension_x": 3840,
                    "dimension_y": 2160,
                }
            ]
        }
        mock_get.return_value = mock_response

        src = WallhavenSource()
        config = get_default_config()
        info = src.fetch("nature", {}, config)

        self.assertEqual(info.source_name, "wallhaven")
        self.assertEqual(info.url, "https://w.wallhaven.cc/full/ab/wallhaven-abc123.jpg")
        self.assertEqual(info.width, 3840)

    @patch("requests.get")
    def test_bing_fetch_mock(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "images": [
                {
                    "url": "/th?id=OHR.TestImage_EN-US12345_1920x1080.jpg",
                    "copyright": "Test Photographer (© Bing)",
                    "title": "Stunning Sunrise",
                }
            ]
        }
        mock_get.return_value = mock_response

        src = BingSource()
        config = get_default_config()
        info = src.fetch("nature", {}, config)

        self.assertEqual(info.source_name, "bing")
        self.assertIn("https://www.bing.com/th?id=OHR.TestImage", info.url)
        self.assertEqual(info.photographer, "Test Photographer (© Bing)")

    @patch("requests.get")
    def test_disabled_sources_omitted_from_chain(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "images": [
                {
                    "url": "/th?id=OHR.BingOnly_1920x1080.jpg",
                    "copyright": "Bing Only",
                }
            ]
        }
        mock_get.return_value = mock_response

        config = get_default_config()
        # Disable all sources except bing
        for src, val in config["sources"].items():
            if isinstance(val, dict):
                val["enabled"] = (src == "bing")

        info, topic = fetch_wallpaper_from_chain(config)
        self.assertEqual(info.source_name, "bing")

    def test_all_sources_disabled_raises(self):
        config = get_default_config()
        for src, val in config["sources"].items():
            if isinstance(val, dict):
                val["enabled"] = False

        with self.assertRaises(RuntimeError):
            fetch_wallpaper_from_chain(config)


if __name__ == "__main__":
    unittest.main()

"""
Tests for awall.widgets
"""

import tempfile
import unittest
from pathlib import Path
from PIL import Image

from awall.widgets import composite_widgets


class TestWidgets(unittest.TestCase):
    def test_composite_widgets_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = Path(tmpdir) / "test.jpg"
            Image.new("RGB", (800, 600), "blue").save(img_path, "JPEG")

            config = {"widgets": {"enabled": False}}
            out_path = composite_widgets(img_path, config)
            self.assertEqual(out_path, img_path.resolve())

    def test_composite_widgets_enabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = Path(tmpdir) / "test.jpg"
            Image.new("RGB", (1280, 720), "darkblue").save(img_path, "JPEG")

            config = {
                "widgets": {
                    "enabled": True,
                    "position": "center",
                    "show_clock": True,
                    "show_weather": False,
                    "show_media": False,
                    "show_quote": False,
                    "backdrop": True,
                }
            }
            out_path = composite_widgets(img_path, config)
            self.assertTrue(out_path.exists())
            with Image.open(out_path) as res_img:
                self.assertEqual(res_img.size, (1280, 720))


if __name__ == "__main__":
    unittest.main()

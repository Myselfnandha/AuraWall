"""
Unit tests for multi-monitor per-display wallpaper configuration and dispatch.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

import awall.lockscreen
from awall.monitor import MonitorInfo
from awall.wallpaper_setter import set_wallpaper_multi


class TestMultiMonitor(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.target_dir = Path(self.tmp_dir.name)

        self.img1 = self.target_dir / "mon1.jpg"
        self.img2 = self.target_dir / "mon2.jpg"

        Image.new("RGB", (100, 100), color="blue").save(self.img1)
        Image.new("RGB", (100, 100), color="green").save(self.img2)

    def tearDown(self):
        self.tmp_dir.cleanup()

    @patch("awall.wallpaper_setter.detect_backend")
    def test_set_wallpaper_multi(self, mock_detect):
        mock_backend = MagicMock()
        mock_backend.name = "xfdesktop"
        mock_backend.set_wallpaper.return_value = True
        mock_detect.return_value = mock_backend

        images = {
            "eDP-1": self.img1,
            "HDMI-1": self.img2,
        }

        ok = set_wallpaper_multi(images, scaling="fill")
        self.assertTrue(ok)
        self.assertEqual(mock_backend.set_wallpaper.call_count, 2)

    @patch("awall.daemon.save_config")
    @patch("awall.monitor.get_monitors")
    @patch("awall.wallpaper_setter.set_wallpaper_multi", return_value=True)
    @patch("awall.lockscreen.sync_lock_screen")
    @patch("awall.daemon.fetch_wallpaper_from_chain")
    def test_daemon_per_monitor_rotation(self, mock_fetch, mock_sync, mock_multi, mock_monitors, mock_save):
        from awall.daemon import change_wallpaper
        from awall.sources.base import WallpaperInfo

        mock_monitors.return_value = [
            MonitorInfo(name="eDP-1", width=1920, height=1080, is_primary=True),
            MonitorInfo(name="HDMI-1", width=1920, height=1080, is_primary=False),
        ]

        wp1 = WallpaperInfo(url="", source_name="local", local_path=str(self.img1), photographer="Test1")
        wp2 = WallpaperInfo(url="", source_name="local", local_path=str(self.img2), photographer="Test2")
        mock_fetch.side_effect = [(wp1, "nature"), (wp2, "architecture")]

        config = {
            "paused": False,
            "display": {
                "multi_monitor": "per_monitor",
                "monitor_config": {
                    "eDP-1": {"mode": "unique"},
                    "HDMI-1": {"mode": "unique"},
                },
                "scaling": "fill",
                "lock_screen": {"enabled": True},
            },
            "dynamic": {"enabled": False},
            "cache": {"directory": str(self.target_dir), "max_wallpapers": 10},
            "notifications": {"enabled": False},
            "wallpaper_backend": "auto",
        }

        ok = change_wallpaper(config=config, ignore_pause=True)
        self.assertTrue(ok)
        mock_multi.assert_called_once()
        mock_sync.assert_called_once()


if __name__ == "__main__":
    unittest.main()

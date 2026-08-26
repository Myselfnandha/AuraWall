"""
Unit tests for Lock Screen Rotate on Sign-in / Unlock and DBus event listener.
"""

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image

from awall.lock_listener import LockScreenEventListener, rotate_lock_screen_on_unlock
from awall.sources.base import WallpaperInfo


class TestLockListener(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.test_img = Path(self.tmp_dir.name) / "test_wall.jpg"
        Image.new("RGB", (1920, 1080), color=(50, 150, 200)).save(self.test_img)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_rotate_on_unlock_disabled(self):
        config = {
            "display": {
                "lock_screen": {
                    "enabled": True,
                    "rotate_on_unlock": False,
                }
            }
        }
        res = rotate_lock_screen_on_unlock(config)
        self.assertFalse(res)

    @patch("awall.daemon.change_wallpaper", return_value=True)
    def test_rotate_on_unlock_sync_desktop(self, mock_change):
        config = {
            "display": {
                "lock_screen": {
                    "enabled": True,
                    "rotate_on_unlock": True,
                    "unlock_mode": "sync_desktop",
                }
            }
        }
        res = rotate_lock_screen_on_unlock(config)
        self.assertTrue(res)
        mock_change.assert_called_once()

    @patch("awall.cache.CacheManager.get_offline_wallpaper")
    @patch("awall.lock_listener.sync_lock_screen", return_value=True)
    def test_rotate_on_unlock_favorites_cache(self, mock_sync, mock_offline):
        mock_offline.return_value = self.test_img
        config = {
            "display": {
                "lock_screen": {
                    "enabled": True,
                    "rotate_on_unlock": True,
                    "unlock_mode": "favorites_cache",
                }
            }
        }
        res = rotate_lock_screen_on_unlock(config)
        self.assertTrue(res)
        mock_sync.assert_called_once_with(self.test_img, config)

    @patch("awall.sources.fetch_wallpaper_from_chain")
    @patch("awall.lock_listener.sync_lock_screen", return_value=True)
    def test_rotate_on_unlock_independent(self, mock_sync, mock_fetch):
        wp = WallpaperInfo(url="", source_name="local", local_path=str(self.test_img))
        mock_fetch.return_value = (wp, "nature")
        config = {
            "display": {
                "lock_screen": {
                    "enabled": True,
                    "rotate_on_unlock": True,
                    "unlock_mode": "independent",
                }
            }
        }
        res = rotate_lock_screen_on_unlock(config)
        self.assertTrue(res)
        mock_sync.assert_called_once()

    def test_listener_debouncing(self):
        calls = []
        listener = LockScreenEventListener(on_unlock_callback=lambda: calls.append(True))
        listener.debounce_seconds = 1.0

        # First trigger fires
        listener._trigger_unlock_event()
        self.assertEqual(len(calls), 1)

        # Immediate second trigger is debounced
        listener._trigger_unlock_event()
        self.assertEqual(len(calls), 1)

        # After debounce window expires, next trigger fires
        listener.last_unlock_time = time.time() - 2.0
        listener._trigger_unlock_event()
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()

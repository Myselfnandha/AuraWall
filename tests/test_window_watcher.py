"""
Tests for active window detection and event-driven smart rotation watcher.
"""

import time
import unittest
from unittest.mock import MagicMock, patch

from awall.window_watcher import (
    SmartRotationWatcher,
    check_is_desktop_active,
)


class TestWindowWatcher(unittest.TestCase):
    def test_smart_watcher_pauses_when_app_active(self):
        trigger_mock = MagicMock()
        desktop_mock = MagicMock(return_value=False)  # Application active

        watcher = SmartRotationWatcher(
            on_trigger_callback=trigger_mock,
            desktop_check_func=desktop_mock,
        )
        with patch.object(watcher, "_event_listener_loop"):
            watcher.start()

            # Window event arrives (app is active)
            watcher.on_window_focus_changed()

            # Should not trigger and timer should be cancelled
            trigger_mock.assert_not_called()
            self.assertFalse(watcher.was_desktop)
            self.assertIsNone(watcher._timer)

            watcher.stop()

    @patch("awall.window_watcher.load_config")
    def test_smart_watcher_immediate_rotation_when_overdue(self, mock_cfg):
        mock_cfg.return_value = {
            "paused": False,
            "schedule": {"interval_minutes": 5, "pause_on_active_window": True},
        }
        trigger_mock = MagicMock()
        is_desktop_state = [False]  # Start with app active

        def get_desktop():
            return is_desktop_state[0]

        watcher = SmartRotationWatcher(
            on_trigger_callback=trigger_mock,
            desktop_check_func=get_desktop,
        )
        with patch.object(watcher, "_event_listener_loop"):
            watcher.start()

            # Set last change time to 10 minutes ago (interval is 5 min = 300s)
            watcher.last_change_time = time.time() - 600
            watcher.was_desktop = False

            # User returns to Desktop!
            is_desktop_state[0] = True
            watcher.on_window_focus_changed()

            # Must have triggered immediately upon returning to desktop!
            trigger_mock.assert_called_once()
            self.assertTrue(watcher.was_desktop)

            watcher.stop()

    @patch("awall.window_watcher.load_config")
    def test_smart_watcher_no_premature_rotation_if_within_interval(self, mock_cfg):
        mock_cfg.return_value = {
            "paused": False,
            "schedule": {"interval_minutes": 5, "pause_on_active_window": True},
        }
        trigger_mock = MagicMock()
        is_desktop_state = [False]

        def get_desktop():
            return is_desktop_state[0]

        watcher = SmartRotationWatcher(
            on_trigger_callback=trigger_mock,
            desktop_check_func=get_desktop,
        )
        with patch.object(watcher, "_event_listener_loop"):
            watcher.start()

            # Set last change time to only 30 seconds ago
            watcher.last_change_time = time.time() - 30
            watcher.was_desktop = False

            # User returns to Desktop
            is_desktop_state[0] = True
            watcher.on_window_focus_changed()

            # Should NOT trigger immediately since 30s < 300s
            trigger_mock.assert_not_called()
            self.assertTrue(watcher.was_desktop)
            # Should have armed timer for remaining time
            self.assertIsNotNone(watcher._timer)

            watcher.stop()


if __name__ == "__main__":
    unittest.main()

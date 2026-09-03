"""
Smart desktop event watcher and power-saving rotation scheduler for awall.
Features:
- Event-driven non-polling notification via kernel sockets and X11 _NET_ACTIVE_WINDOW spy.
- True interval freezing: pauses the countdown timer while in applications or fullscreen gaming/videos.
- Seamless continuation: continues counting down from the exact saved remaining time when returning to the desktop.
- 0% CPU consumption and 0 wakeups while application windows are focused.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

from awall.config import load_config
from awall.daemon import change_wallpaper


def check_active_window_state() -> Tuple[bool, bool]:
    """
    Checks the current active window state.
    Returns (is_desktop, is_fullscreen).
    """
    # 1. Hyprland (Wayland)
    if shutil.which("hyprctl") and os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        try:
            out = subprocess.check_output(["hyprctl", "activewindow", "-j"], timeout=1).decode("utf-8")
            data = json.loads(out)
            if not data or (not data.get("class") and not data.get("title")):
                return True, False
            is_fullscreen = bool(data.get("fullscreen", False))
            return False, is_fullscreen
        except Exception:
            pass

    # 2. Sway (Wayland)
    if shutil.which("swaymsg") and os.environ.get("SWAYSOCK"):
        try:
            out = subprocess.check_output(["swaymsg", "-t", "get_tree"], timeout=1).decode("utf-8")
            data = json.loads(out)

            def find_focused(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
                if node.get("focused"):
                    return node
                for child in node.get("nodes", []) + node.get("floating_nodes", []):
                    f = find_focused(child)
                    if f:
                        return f
                return None

            focused = find_focused(data)
            if not focused or focused.get("type") == "workspace" or not (focused.get("app_id") or focused.get("window_properties")):
                return True, False
            is_fullscreen = bool(focused.get("fullscreen_mode", 0) > 0)
            return False, is_fullscreen
        except Exception:
            pass

    # 3. X11 (via xprop)
    if shutil.which("xprop"):
        try:
            root_out = subprocess.check_output(
                ["xprop", "-root", "_NET_SHOWING_DESKTOP", "_NET_ACTIVE_WINDOW"],
                stderr=subprocess.DEVNULL,
                timeout=1,
            ).decode("utf-8")

            # Check if "Show Desktop" is active
            if re.search(r"_NET_SHOWING_DESKTOP\(CARDINAL\)\s*=\s*1", root_out):
                return True, False

            match = re.search(r"_NET_ACTIVE_WINDOW.*?#\s*(0x[0-9a-fA-F]+)", root_out)
            if not match:
                return True, False
            wid = match.group(1)
            if wid in ("0x0", "0x00000000") or int(wid, 16) == 0:
                return True, False

            wout = subprocess.check_output(
                ["xprop", "-id", wid, "_NET_WM_WINDOW_TYPE", "WM_CLASS", "_NET_WM_STATE"],
                stderr=subprocess.DEVNULL,
                timeout=1,
            ).decode("utf-8")

            if "_NET_WM_WINDOW_TYPE_DESKTOP" in wout:
                return True, False

            desktop_classes = {
                "xfdesktop",
                "desktop",
                "nautilus",
                "nemo",
                "caja",
                "pcmanfm",
                "plasma-desktop",
                "plasmashell",
                "gnome-shell",
                "kded5",
                "kded6",
            }
            wout_lower = wout.lower()
            for dc in desktop_classes:
                if dc in wout_lower:
                    return True, False

            is_fullscreen = "_NET_WM_STATE_FULLSCREEN" in wout
            return False, is_fullscreen
        except Exception:
            return True, False

    # 4. Fallback: xdotool
    if shutil.which("xdotool"):
        try:
            wid_raw = subprocess.check_output(
                ["xdotool", "getactivewindow"],
                stderr=subprocess.DEVNULL,
                timeout=1,
            ).decode("utf-8").strip()
            return (not bool(wid_raw)), False
        except Exception:
            return True, False

    return True, False


def check_is_desktop_active() -> bool:
    """Checks if the desktop is currently focused."""
    is_desktop, _ = check_active_window_state()
    return is_desktop


class SmartRotationWatcher:
    """
    Event-driven rotation watcher with True Interval Pausing and Resuming.
    - Consumes 0 CPU and 0 timer wakeups while applications or fullscreen games/videos are active.
    - Freezes the timer at its exact remaining seconds when switching to apps.
    - Continues counting down seamlessly from the saved remaining time when returning to desktop.
    """

    def __init__(
        self,
        on_trigger_callback: Optional[Callable[[], None]] = None,
        desktop_check_func: Optional[Callable[[], bool]] = None,
    ):
        self.on_trigger = on_trigger_callback if on_trigger_callback is not None else self._default_trigger
        self.check_desktop = desktop_check_func or check_is_desktop_active
        self.last_change_time = time.time()
        self.remaining_seconds: float = float(self._get_interval_sec())
        self.active_desktop_start: Optional[float] = None
        self.is_fullscreen: bool = False
        self.was_desktop = self.check_desktop()
        if self.was_desktop:
            self.active_desktop_start = time.time()
        self.running = False
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._listener_thread: Optional[threading.Thread] = None
        self._proc: Optional[subprocess.Popen] = None

    def _default_trigger(self):
        change_wallpaper(ignore_pause=False)

    def _get_interval_sec(self) -> int:
        config = load_config()
        sched_cfg = config.get("schedule", {})
        interval_min = sched_cfg.get("interval_minutes", 5)
        return max(10, interval_min * 60)

    def _get_remaining_float(self) -> float:
        """Returns the current remaining seconds without modifying internal state."""
        if self.was_desktop and self.active_desktop_start is not None:
            elapsed = time.time() - self.active_desktop_start
            return max(0.0, self.remaining_seconds - elapsed)
        return max(0.0, self.remaining_seconds)

    def record_change(self):
        """Resets the interval timer after a wallpaper change."""
        with self._lock:
            self.last_change_time = time.time()
            self.remaining_seconds = float(self._get_interval_sec())
            if self.was_desktop:
                self.active_desktop_start = time.time()
            else:
                self.active_desktop_start = None
            self._arm_timer_if_needed()

    def update_pause_state(self):
        """Re-evaluates paused state immediately and stops/arms timer accordingly."""
        with self._lock:
            config = load_config()
            if config.get("paused", False):
                self._cancel_timer()
            else:
                self._arm_timer_if_needed()

    def start(self):
        """Starts the event-driven watcher thread."""
        with self._lock:
            if self.running:
                return
            self.running = True
            self.last_change_time = time.time()
            self.remaining_seconds = float(self._get_interval_sec())
            self.was_desktop = self.check_desktop()
            if self.was_desktop:
                self.active_desktop_start = time.time()
            else:
                self.active_desktop_start = None
            self._arm_timer_if_needed()

        self._listener_thread = threading.Thread(target=self._event_listener_loop, daemon=True)
        self._listener_thread.start()

    def stop(self):
        """Stops the watcher and cleans up subprocess/timers."""
        with self._lock:
            self.running = False
            self._cancel_timer()
            proc = self._proc
            self._proc = None

        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=0.5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            if proc.stdout:
                try:
                    proc.stdout.close()
                except Exception:
                    pass

    def get_remaining_time_sec(self) -> Tuple[int, bool, str]:
        """
        Returns (remaining_seconds, is_paused, display_text).
        display_text is e.g. '04:32', '⏸ 03:20', or 'Paused'.
        """
        config = load_config()
        if config.get("paused", False):
            return 0, True, "Paused"

        rem_float = self._get_remaining_float()
        rem_sec = max(0, int(rem_float))
        mins, secs = divmod(rem_sec, 60)

        pause_on_window = config.get("schedule", {}).get("pause_on_active_window", True)
        if pause_on_window and not self.was_desktop:
            tag = "⏸ Fullscreen" if getattr(self, "is_fullscreen", False) else "⏸ In App"
            return rem_sec, False, f"⏸ {mins:02d}:{secs:02d}"

        return rem_sec, False, f"{mins:02d}:{secs:02d}"

    def _cancel_timer(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _arm_timer_if_needed(self):
        """Arms the timer only if on desktop and rotation is active."""
        self._cancel_timer()
        if not self.running:
            return

        config = load_config()
        if config.get("paused", False):
            return

        pause_on_window = config.get("schedule", {}).get("pause_on_active_window", True)
        if pause_on_window and not self.was_desktop:
            # Application / Fullscreen active -> Stay dormant with frozen timer!
            return

        rem = self._get_remaining_float()
        if rem <= 0.0:
            self._on_timer_fired()
            return

        self.remaining_seconds = rem
        self.active_desktop_start = time.time()
        self._timer = threading.Timer(max(0.5, rem), self._on_timer_fired)
        self._timer.daemon = True
        self._timer.start()

    def _on_timer_fired(self):
        """Called when interval expires while on desktop."""
        with self._lock:
            if not self.running:
                return

            config = load_config()
            if config.get("paused", False):
                return

            pause_on_window = config.get("schedule", {}).get("pause_on_active_window", True)
            is_desktop = self.check_desktop() if pause_on_window else True

            if is_desktop:
                self.last_change_time = time.time()
                self.remaining_seconds = float(self._get_interval_sec())
                self.active_desktop_start = time.time()
                self.was_desktop = True
                self.on_trigger()
                self._arm_timer_if_needed()
            else:
                # App active -> mark overdue to trigger upon desktop return
                self.was_desktop = False
                self.remaining_seconds = 0.0
                self.active_desktop_start = None
                self._cancel_timer()

    def on_window_focus_changed(self):
        """
        Called when OS notifies of an active window focus change.
        """
        with self._lock:
            if not self.running:
                return

            config = load_config()
            if config.get("paused", False):
                self._cancel_timer()
                return

            pause_on_window = config.get("schedule", {}).get("pause_on_active_window", True)
            if not pause_on_window:
                return

            is_desktop, is_fullscreen = check_active_window_state() if self.check_desktop == check_is_desktop_active else (self.check_desktop(), False)
            self.is_fullscreen = is_fullscreen

            if not is_desktop:
                # Switched to Application / Fullscreen -> Freeze and hold remaining time!
                if self.was_desktop:
                    if self.active_desktop_start is not None:
                        elapsed = time.time() - self.active_desktop_start
                        self.remaining_seconds = max(0.0, self.remaining_seconds - elapsed)
                        self.active_desktop_start = None
                    self.was_desktop = False
                    self._cancel_timer()
                return

            # Switched back to Desktop!
            if not self.was_desktop:
                self.was_desktop = True
                if self.remaining_seconds <= 0.0:
                    # OVERDUE! Rotate immediately upon returning to desktop
                    self.last_change_time = time.time()
                    self.remaining_seconds = float(self._get_interval_sec())
                    self.active_desktop_start = time.time()
                    self.on_trigger()
                    self._arm_timer_if_needed()
                else:
                    # Continue countdown from frozen remaining time!
                    self.active_desktop_start = time.time()
                    self._arm_timer_if_needed()

    def _event_listener_loop(self):
        """
        Listens to system triggers (X11 event stream / Hyprland / Sway socket)
        blocking on kernel socket without polling.
        """
        # 1. Hyprland Event Socket
        hypr_sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        hypr_sock = f"/tmp/hypr/{hypr_sig}/.socket2.sock" if hypr_sig else ""
        xdg_hypr = f"{os.environ.get('XDG_RUNTIME_DIR', '')}/hypr/{hypr_sig}/.socket2.sock" if hypr_sig else ""
        chosen_sock = xdg_hypr if os.path.exists(xdg_hypr) else (hypr_sock if os.path.exists(hypr_sock) else None)

        if chosen_sock and os.path.exists(chosen_sock):
            try:
                client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                client.connect(chosen_sock)
                with client.makefile("r", encoding="utf-8") as f:
                    while self.running:
                        line = f.readline()
                        if not line:
                            break
                        if line.startswith("activewindow>>") or line.startswith("workspace>>"):
                            self.on_window_focus_changed()
                return
            except Exception:
                pass

        # 2. Sway IPC Event Stream
        if shutil.which("swaymsg") and os.environ.get("SWAYSOCK"):
            try:
                self._proc = subprocess.Popen(
                    ["swaymsg", "-t", "subscribe", "-m", '["window", "workspace"]'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                while self.running and self._proc.poll() is None:
                    line = self._proc.stdout.readline()
                    if line:
                        self.on_window_focus_changed()
                return
            except Exception:
                pass

        # 3. X11 via xprop -spy (System Event Hook)
        if shutil.which("xprop") and (os.environ.get("DISPLAY") or not os.environ.get("WAYLAND_DISPLAY")):
            try:
                self._proc = subprocess.Popen(
                    ["xprop", "-spy", "-root", "_NET_ACTIVE_WINDOW", "_NET_SHOWING_DESKTOP", "_NET_CURRENT_DESKTOP"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                while self.running and self._proc.poll() is None:
                    line = self._proc.stdout.readline()
                    if line:
                        self.on_window_focus_changed()
                return
            except Exception:
                pass

        # Fallback if no system trigger is available: check periodically
        while self.running:
            time.sleep(2)
            self.on_window_focus_changed()


# Backward compatibility alias
SmartRotationManager = SmartRotationWatcher

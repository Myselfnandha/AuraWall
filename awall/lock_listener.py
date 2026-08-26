"""
DBus Screen Lock/Unlock and Sign-in event listener for awall.
Listens for screensaver and session unlock events with 0% CPU consumption
and triggers configured lock screen wallpaper rotation strategies.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib

from awall.cache import CacheManager
from awall.config import load_config
from awall.lockscreen import sync_lock_screen


def rotate_lock_screen_on_unlock(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Executes the configured lock screen rotation strategy upon sign-in / unlock:
    - 'independent': Fetches and applies a fresh new wallpaper exclusively to the lock screen.
    - 'sync_desktop': Triggers synchronized rotation of both desktop and lock screen.
    - 'favorites_cache': Applies a random wallpaper from favorites/cache to the lock screen.
    """
    if config is None:
        config = load_config()

    lock_cfg = config.get("display", {}).get("lock_screen", {})
    if not lock_cfg.get("enabled", True) or not lock_cfg.get("rotate_on_unlock", True):
        return False

    mode = lock_cfg.get("unlock_mode", "independent")
    print(f"[awall] Sign-in / Unlock detected. Rotating lock screen (mode: {mode})...")

    if mode == "sync_desktop":
        from awall.daemon import change_wallpaper
        return change_wallpaper(config=config, ignore_pause=True)

    elif mode == "favorites_cache":
        cache_mgr = CacheManager()
        fav_or_cached = cache_mgr.get_offline_wallpaper()
        if fav_or_cached and fav_or_cached.exists():
            return sync_lock_screen(fav_or_cached, config)
        return False

    else:
        # Default 'independent' mode: fetch fresh wallpaper for lockscreen
        try:
            from awall.sources import fetch_wallpaper_from_chain
            wp_info, topic = fetch_wallpaper_from_chain(config)
            cache_mgr = CacheManager()

            if wp_info.local_path and Path(wp_info.local_path).exists():
                local_file = Path(wp_info.local_path)
            elif wp_info.url:
                local_file = cache_mgr.download_image(wp_info.url, source_prefix=f"lock_{wp_info.source_name}")
            else:
                local_file = cache_mgr.get_offline_wallpaper()

            if local_file and local_file.exists():
                ok = sync_lock_screen(local_file, config)
                if ok:
                    print(f"[awall] Successfully updated lock screen: {local_file.name}")
                return ok
        except Exception as e:
            print(f"[awall] Notice: Independent lockscreen rotation error ({e}). Using cached fallback.")
            cache_mgr = CacheManager()
            fallback = cache_mgr.get_offline_wallpaper()
            if fallback and fallback.exists():
                return sync_lock_screen(fallback, config)

    return False


class LockScreenEventListener:
    """Listens for DBus screensaver and logind unlock signals to trigger lock screen rotation."""

    def __init__(self, on_unlock_callback: Optional[Callable[[], None]] = None):
        self.on_unlock_cb = on_unlock_callback or self._default_unlock_handler
        self.last_unlock_time = 0.0
        self.debounce_seconds = 3.0
        self.session_bus: Optional[Gio.DBusConnection] = None
        self.system_bus: Optional[Gio.DBusConnection] = None
        self.subscriptions = []
        self._running = False

    def _default_unlock_handler(self):
        threading.Thread(target=lambda: rotate_lock_screen_on_unlock(), daemon=True).start()

    def start(self):
        """Connects to DBus and subscribes to unlock signals."""
        if self._running:
            return
        self._running = True

        try:
            # 1. Session Bus (ScreenSaver ActiveChanged)
            self.session_bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            if self.session_bus:
                # freedesktop / xfce / gnome screensaver interfaces
                for iface in ("org.freedesktop.ScreenSaver", "org.xfce.ScreenSaver", "org.gnome.ScreenSaver"):
                    sub_id = self.session_bus.signal_subscribe(
                        None,  # sender
                        iface,  # interface
                        "ActiveChanged",  # member
                        None,  # object path
                        None,  # arg0
                        Gio.DBusSignalFlags.NONE,
                        self._on_session_screensaver_signal,
                        None,
                    )
                    self.subscriptions.append((self.session_bus, sub_id))
        except Exception as e:
            print(f"[awall] DBus session bus subscribe notice: {e}")

        try:
            # 2. System Bus (systemd-logind Session Unlock)
            self.system_bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            if self.system_bus:
                sub_id = self.system_bus.signal_subscribe(
                    "org.freedesktop.login1",
                    "org.freedesktop.login1.Session",
                    "Unlock",
                    None,
                    None,
                    Gio.DBusSignalFlags.NONE,
                    self._on_logind_unlock_signal,
                    None,
                )
                self.subscriptions.append((self.system_bus, sub_id))
        except Exception as e:
            print(f"[awall] DBus system bus subscribe notice: {e}")

    def _on_session_screensaver_signal(self, connection, sender, path, iface, signal, params, user_data):
        """Fires when ScreenSaver ActiveChanged(boolean active) signal is emitted."""
        try:
            active = params.get_child_value(0).get_boolean()
            # When active changes from True to False, screen is unlocked / sign in completed
            if not active:
                self._trigger_unlock_event()
        except Exception:
            pass

    def _on_logind_unlock_signal(self, connection, sender, path, iface, signal, params, user_data):
        """Fires when systemd-logind emits Unlock signal on session."""
        self._trigger_unlock_event()

    def _trigger_unlock_event(self):
        """Debounced dispatch of the unlock callback."""
        now = time.time()
        if now - self.last_unlock_time < self.debounce_seconds:
            return
        self.last_unlock_time = now

        if self.on_unlock_cb:
            self.on_unlock_cb()

    def stop(self):
        """Unsubscribes all DBus signal listeners."""
        self._running = False
        for bus, sub_id in self.subscriptions:
            try:
                bus.signal_unsubscribe(sub_id)
            except Exception:
                pass
        self.subscriptions.clear()

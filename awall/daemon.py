"""
Core daemon and wallpaper rotation orchestration for awall.
Coordinates fetching, downloading, transitions, history logging, and dynamic weather/solar synthesis.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

from awall.cache import CacheManager
from awall.config import load_config, save_config
from awall.dynamic_pack import select_dynamic_frame
from awall.history import HistoryManager
from awall.notify import (
    send_error_notification,
    send_offline_notification,
    send_wallpaper_notification,
)
from awall.sources import fetch_wallpaper_from_chain
from awall.transition import apply_transition
from awall.wallpaper_setter import set_wallpaper
from awall.weather import (
    calculate_solar_phase,
    get_live_weather,
    get_location,
    synthesize_dynamic_query,
)


def change_wallpaper(
    config: Optional[Dict[str, Any]] = None,
    force_topic: Optional[str] = None,
    force_source: Optional[str] = None,
    ignore_pause: bool = False,
) -> bool:
    """
    Executes a single wallpaper rotation cycle.
    Returns True if a new wallpaper was successfully set.
    """
    if config is None:
        config = load_config()

    # Check pause state
    if config.get("paused", False) and not ignore_pause:
        print("[awall] Wallpaper rotation is currently PAUSED. Skipping.")
        return False

    cache_cfg = config.get("cache", {})
    cache_mgr = CacheManager(
        cache_dir=cache_cfg.get("directory"),
        max_wallpapers=cache_cfg.get("max_wallpapers", 50),
    )
    history_mgr = HistoryManager()
    curr_entry = history_mgr.get_current()
    old_path = curr_entry.get("file_path") if curr_entry else None

    # Apply temporary source override if requested
    if force_source:
        config["active_source"] = force_source

    display_cfg = config.get("display", {})
    scaling = display_cfg.get("scaling", "fill")
    transition_type = display_cfg.get("transition", "fade")
    duration_ms = display_cfg.get("transition_duration_ms", 500)
    backend_override = config.get("wallpaper_backend", "auto")

    # Dynamic Solar & Weather Query Synthesis
    dyn_cfg = config.get("dynamic", {})
    topic_query = force_topic

    if dyn_cfg.get("enabled", True) and not force_topic:
        lat, lon, _ = get_location(config)
        solar_phase, _ = calculate_solar_phase(lat, lon)
        weather_info = get_live_weather(lat, lon)
        weather_mood = weather_info.get("mood", "clear")

        base_topic = config.get("topics", {}).get("enabled", ["wallpapers"])[0]
        # Generate weather-and-sun-aware search keywords
        topic_query = synthesize_dynamic_query(base_topic, solar_phase, weather_mood)

    # Setter callback for transition animator
    def _setter_cb(p: Path) -> bool:
        return set_wallpaper(
            image_path=p,
            scaling=scaling,
            backend_override=backend_override,
        )

    wallpaper_info = None
    topic_used = topic_query or force_topic or ""
    is_offline = False
    downloaded_file: Optional[Path] = None

    # Fast-Path: Check smart prefetch queue for instantaneous (<50ms) rotation
    from awall.prefetch import PrefetchManager
    prefetch_mgr = PrefetchManager.get_default()

    prefetched = None
    if not force_topic and not force_source:
        prefetched = prefetch_mgr.pop_prefetched(config=config)

    if prefetched and Path(prefetched.get("file_path", "")).exists():
        downloaded_file = Path(prefetched["file_path"])
        photographer = prefetched.get("photographer", "Unknown")
        photographer_url = prefetched.get("photographer_url", "")
        source_name = prefetched.get("source_name", "online")
        topic_used = prefetched.get("topic", "wallpapers")
        url = prefetched.get("url", "")
    else:
        # Attempt fetching from sources
        try:
            wallpaper_info, topic_used = fetch_wallpaper_from_chain(config, topic_override=topic_query)
        except Exception as e:
            print(f"[awall] Notice: Online fetch failed ({e}). Attempting offline cache fallback.")
            is_offline = True

        if wallpaper_info and not is_offline:
            try:
                if wallpaper_info.source_name == "local" and wallpaper_info.local_path:
                    downloaded_file = cache_mgr.save_local_copy(
                        wallpaper_info.local_path, source_prefix="local"
                    )
                else:
                    downloaded_file = cache_mgr.download_image(
                        wallpaper_info.url, source_prefix=wallpaper_info.source_name
                    )
            except Exception as e:
                print(f"[awall] Error downloading wallpaper ({e}). Falling back to cache.")
                is_offline = True

        # Offline fallback
        if is_offline or not downloaded_file:
            downloaded_file = cache_mgr.get_offline_wallpaper(exclude_path=old_path)
            if not downloaded_file:
                err_msg = "No internet connection and no cached wallpapers available."
                print(f"[awall] Error: {err_msg}")
                send_error_notification(err_msg)
                return False

            # Build offline info
            photographer = "Cached"
            photographer_url = ""
            source_name = "cache"
            topic_used = "offline"
            url = ""
        else:
            photographer = wallpaper_info.photographer
            photographer_url = wallpaper_info.photographer_url
            source_name = wallpaper_info.source_name
            url = wallpaper_info.url

        # Prime prefetch buffer in background for subsequent rotations
        prefetch_mgr.trigger_prefetch(config=config)

    # Multi-monitor per-display or unified mode
    multi_mon_mode = display_cfg.get("multi_monitor", "unified")
    monitor_cfg = display_cfg.get("monitor_config", {})

    if multi_mon_mode == "per_monitor":
        from awall.monitor import get_monitors
        from awall.wallpaper_setter import set_wallpaper_multi

        monitors = get_monitors()
        monitor_images: Dict[str, Path] = {}

        for mon in monitors:
            mode = monitor_cfg.get(mon.name, {}).get("mode", "unique")
            if mon.is_primary or mode == "shared" or not monitor_images:
                # Primary or shared with primary
                monitor_images[mon.name] = downloaded_file
            else:
                # Unique wallpaper for this monitor: attempt fetching a secondary image
                secondary_file: Optional[Path] = None
                try:
                    sec_info, _ = fetch_wallpaper_from_chain(config, topic_override=topic_query)
                    if sec_info and sec_info.url:
                        secondary_file = cache_mgr.download_image(
                            sec_info.url, source_prefix=sec_info.source_name
                        )
                except Exception:
                    pass
                if not secondary_file:
                    secondary_file = cache_mgr.get_offline_wallpaper(exclude_path=str(downloaded_file))
                monitor_images[mon.name] = secondary_file or downloaded_file

        success = set_wallpaper_multi(
            images=monitor_images,
            scaling=scaling,
            backend_override=backend_override,
        )
    else:
        # Apply unified wallpaper with transition
        success = apply_transition(
            old_path=old_path,
            new_path=downloaded_file,
            transition_type=transition_type,
            duration_ms=duration_ms,
            setter_func=_setter_cb,
            scaling=scaling,
        )

    if not success:
        print("[awall] Failed to apply wallpaper to desktop.")
        return False

    # Sync Lock Screen Wallpaper
    try:
        from awall.lockscreen import sync_lock_screen
        sync_lock_screen(image_path=downloaded_file, config=config)
    except Exception as e:
        print(f"[awall] Lock screen sync error: {e}")

    # Log to history
    history_mgr.add_entry(
        source=source_name,
        file_path=str(downloaded_file),
        url=url,
        photographer=photographer,
        photographer_url=photographer_url,
        topic=topic_used,
        width=wallpaper_info.width if wallpaper_info else None,
        height=wallpaper_info.height if wallpaper_info else None,
    )

    # Notifications
    notify_cfg = config.get("notifications", {})
    if is_offline:
        if notify_cfg.get("enabled", True):
            send_offline_notification(image_path=downloaded_file)
    else:
        send_wallpaper_notification(
            photographer=photographer,
            topic=topic_used,
            source=source_name,
            image_path=downloaded_file,
            photographer_url=photographer_url,
            enabled=notify_cfg.get("enabled", True),
            show_credits=notify_cfg.get("show_credits", True),
        )

    # Save any sequential progression in config
    save_config(config)

    print(f"[awall] Successfully updated wallpaper: {downloaded_file.name} ({photographer})")
    return True

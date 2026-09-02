"""
Background multi-slot prefetch manager for awall.
Maintains a 5-slot pre-downloaded wallpaper queue so even aggressive/rapid
"Next Wallpaper" clicks change the screen instantaneously (<10ms) with 0 network lag.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from awall.cache import CacheManager, get_default_cache_dir
from awall.config import load_config
from awall.sources import fetch_wallpaper_from_chain
from awall.weather import (
    calculate_solar_phase,
    get_live_weather,
    get_location,
    synthesize_dynamic_query,
)

QUEUE_MAX_SIZE = 5


class PrefetchManager:
    """Manages a multi-slot background prefetch queue for instantaneous wallpaper rotation."""

    _instance: Optional[PrefetchManager] = None
    _lock = threading.Lock()

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else get_default_cache_dir()
        self.queue_file = self.cache_dir / "prefetch_queue.json"
        self.meta_file = self.cache_dir / "prefetch_meta.json"  # legacy single-item compatibility
        self.cache_mgr = CacheManager(cache_dir=self.cache_dir)
        self._is_prefetching = False

    @classmethod
    def get_default(cls) -> PrefetchManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = PrefetchManager()
            return cls._instance

    def _read_queue(self) -> List[Dict[str, Any]]:
        """Reads and validates all active items currently in the prefetch queue."""
        items: List[Dict[str, Any]] = []
        if self.queue_file.exists():
            try:
                raw = json.loads(self.queue_file.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    for entry in raw:
                        fp = Path(entry.get("file_path", ""))
                        if fp.exists() and fp.stat().st_size > 0:
                            items.append(entry)
            except Exception:
                pass

        # Also check legacy single-item file if queue was empty
        if not items and self.meta_file.exists():
            try:
                entry = json.loads(self.meta_file.read_text(encoding="utf-8"))
                fp = Path(entry.get("file_path", ""))
                if fp.exists() and fp.stat().st_size > 0:
                    items.append(entry)
                    self._write_queue(items)
                self.meta_file.unlink(missing_ok=True)
            except Exception:
                pass

        return items

    def _write_queue(self, items: List[Dict[str, Any]]):
        """Persists the validated queue to disk."""
        try:
            self.queue_file.write_text(json.dumps(items, indent=2), encoding="utf-8")
        except Exception:
            pass

    def get_queue_length(self) -> int:
        """Returns number of ready pre-downloaded items."""
        with self._lock:
            return len(self._read_queue())

    def get_prefetched(self) -> Optional[Dict[str, Any]]:
        """Returns the first available ready item without removing it."""
        with self._lock:
            items = self._read_queue()
            return items[0] if items else None

    def pop_prefetched(self, config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Consumes the next pre-downloaded wallpaper from the queue
        and triggers background replenishment.
        """
        popped = None
        with self._lock:
            items = self._read_queue()
            if items:
                popped = items.pop(0)
                self._write_queue(items)

        # Trigger background refill if queue has room
        self.trigger_prefetch(config=config)
        return popped

    def get_instant_fallback(self, exclude_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Instant 0ms fallback for burst rapid-clicking when queue is momentarily empty.
        Picks a fresh cached image so screen changes immediately without blocking.
        """
        cached_file = self.cache_mgr.get_offline_wallpaper(exclude_path=exclude_path)
        if not cached_file or not cached_file.exists():
            return None

        # Build fallback metadata
        clean_name = cached_file.stem
        return {
            "file_path": str(cached_file.resolve()),
            "photographer": "Cached Library",
            "photographer_url": "",
            "source_name": "cache",
            "url": "",
            "topic": clean_name.split("_")[0] if "_" in clean_name else "wallpaper",
            "width": 1920,
            "height": 1080,
            "timestamp": time.time(),
        }

    def trigger_prefetch(self, config: Optional[Dict[str, Any]] = None, target_count: int = QUEUE_MAX_SIZE):
        """Asynchronously replenishes the prefetch buffer until target_count is reached."""
        with self._lock:
            if self._is_prefetching:
                return
            items = self._read_queue()
            if len(items) >= target_count:
                return
            self._is_prefetching = True

        thread = threading.Thread(
            target=self._prefetch_worker,
            args=(config, target_count),
            daemon=True,
            name="awall-prefetch-worker",
        )
        thread.start()

    def _prefetch_worker(self, config: Optional[Dict[str, Any]] = None, target_count: int = QUEUE_MAX_SIZE):
        """Worker thread that fetches and downloads until the queue has target_count items."""
        try:
            cfg = config or load_config()
            if cfg.get("paused", False):
                return

            while True:
                with self._lock:
                    items = self._read_queue()
                    if len(items) >= target_count:
                        break

                # Build topic query if dynamic weather is active
                topic_query = None
                dyn_cfg = cfg.get("dynamic", {})
                if dyn_cfg.get("enabled", True):
                    try:
                        lat, lon, _ = get_location(cfg)
                        solar_phase, _ = calculate_solar_phase(lat, lon)
                        weather_info = get_live_weather(lat, lon)
                        weather_mood = weather_info.get("mood", "clear")
                        base_topic = cfg.get("topics", {}).get("enabled", ["wallpapers"])[0]
                        topic_query = synthesize_dynamic_query(base_topic, solar_phase, weather_mood)
                    except Exception:
                        topic_query = None

                # Fetch from source chain
                wallpaper_info, topic_used = fetch_wallpaper_from_chain(cfg, topic_override=topic_query)
                if not wallpaper_info:
                    break

                # Download
                if wallpaper_info.source_name == "local" and wallpaper_info.local_path:
                    downloaded_file = self.cache_mgr.save_local_copy(
                        wallpaper_info.local_path, source_prefix="local"
                    )
                else:
                    downloaded_file = self.cache_mgr.download_image(
                        wallpaper_info.url, source_prefix=wallpaper_info.source_name
                    )

                if not downloaded_file or not downloaded_file.exists():
                    break

                payload = {
                    "file_path": str(downloaded_file.resolve()),
                    "photographer": wallpaper_info.photographer,
                    "photographer_url": wallpaper_info.photographer_url,
                    "source_name": wallpaper_info.source_name,
                    "url": wallpaper_info.url,
                    "topic": topic_used,
                    "width": wallpaper_info.width,
                    "height": wallpaper_info.height,
                    "timestamp": time.time(),
                }

                with self._lock:
                    items = self._read_queue()
                    if len(items) < target_count:
                        items.append(payload)
                        self._write_queue(items)

                time.sleep(0.15)  # brief throttle between background downloads

        except Exception:
            pass
        finally:
            with self._lock:
                self._is_prefetching = False

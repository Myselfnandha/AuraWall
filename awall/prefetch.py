"""
Background prefetch manager for awall.
Maintains a pre-downloaded wallpaper in a ready queue so clicking "Next Wallpaper"
switches the screen instantaneously (<50ms) without any network waiting.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from awall.cache import CacheManager, get_default_cache_dir
from awall.config import load_config
from awall.sources import fetch_wallpaper_from_chain
from awall.weather import (
    calculate_solar_phase,
    get_live_weather,
    get_location,
    synthesize_dynamic_query,
)


class PrefetchManager:
    """Manages the background prefetch queue for instant wallpaper rotation."""

    _instance: Optional[PrefetchManager] = None
    _lock = threading.Lock()

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else get_default_cache_dir()
        self.meta_file = self.cache_dir / "prefetch_meta.json"
        self.cache_mgr = CacheManager(cache_dir=self.cache_dir)
        self._is_prefetching = False

    @classmethod
    def get_default(cls) -> PrefetchManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = PrefetchManager()
            return cls._instance

    def get_prefetched(self) -> Optional[Dict[str, Any]]:
        """Returns the currently buffered wallpaper info if valid and exists on disk."""
        with self._lock:
            if not self.meta_file.exists():
                return None
            try:
                data = json.loads(self.meta_file.read_text(encoding="utf-8"))
                file_path = Path(data.get("file_path", ""))
                if file_path.exists() and file_path.stat().st_size > 0:
                    return data
            except Exception:
                pass
            return None

    def pop_prefetched(self, config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Consumes the prefetched wallpaper and immediately triggers
        background replenishment for the subsequent cycle.
        """
        item = None
        with self._lock:
            if self.meta_file.exists():
                try:
                    data = json.loads(self.meta_file.read_text(encoding="utf-8"))
                    file_path = Path(data.get("file_path", ""))
                    if file_path.exists() and file_path.stat().st_size > 0:
                        item = data
                except Exception:
                    pass
                try:
                    self.meta_file.unlink(missing_ok=True)
                except Exception:
                    pass

        # Trigger replenishment in background thread
        self.trigger_prefetch(config=config)
        return item

    def trigger_prefetch(self, config: Optional[Dict[str, Any]] = None):
        """Asynchronously replenishes the prefetch buffer if empty."""
        with self._lock:
            if self._is_prefetching:
                return
            self._is_prefetching = True

        thread = threading.Thread(
            target=self._prefetch_worker,
            args=(config,),
            daemon=True,
            name="awall-prefetch-worker",
        )
        thread.start()

    def _prefetch_worker(self, config: Optional[Dict[str, Any]] = None):
        """Worker thread that fetches and downloads 1 fresh wallpaper into the buffer."""
        try:
            cfg = config or load_config()
            if cfg.get("paused", False):
                return

            # Check if valid buffer already exists
            existing = self.get_prefetched()
            if existing:
                return

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
                return

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
                return

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
                self.meta_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        except Exception:
            # Prefetch failures are silent non-fatal background operations
            pass
        finally:
            with self._lock:
                self._is_prefetching = False

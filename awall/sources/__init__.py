"""
Source plugin registry and fallback orchestrator for awall.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from awall.sources.base import WallpaperInfo, WallpaperSource
from awall.sources.unsplash import UnsplashSource
from awall.sources.pexels import PexelsSource
from awall.sources.pixabay import PixabaySource
from awall.sources.reddit import RedditSource
from awall.sources.local import LocalSource

ALL_SOURCES: Dict[str, WallpaperSource] = {
    "unsplash": UnsplashSource(),
    "pexels": PexelsSource(),
    "pixabay": PixabaySource(),
    "reddit": RedditSource(),
    "local": LocalSource(),
}


def get_source(name: str) -> Optional[WallpaperSource]:
    """Retrieve source instance by name."""
    return ALL_SOURCES.get(name.lower())


def pick_next_topic(config: Dict[str, Any]) -> str:
    """Select the next topic according to topic mode (mixed vs sequential)."""
    topics_cfg = config.get("topics", {})
    enabled_topics = topics_cfg.get("enabled", [])
    if not enabled_topics:
        return "wallpapers"

    mode = topics_cfg.get("mode", "mixed")
    if mode == "sequential":
        idx = topics_cfg.get("current_index", 0) % len(enabled_topics)
        chosen = enabled_topics[idx]
        # Increment index in config for sequential progression
        topics_cfg["current_index"] = (idx + 1) % len(enabled_topics)
        return chosen

    return random.choice(enabled_topics)


def fetch_wallpaper_from_chain(
    config: Dict[str, Any],
    topic_override: Optional[str] = None,
) -> Tuple[WallpaperInfo, str]:
    """
    Executes the fallback chain across enabled sources until a wallpaper is successfully found.
    Returns (WallpaperInfo, topic_used).
    Raises RuntimeError if all enabled sources fail.
    """
    topic = topic_override or pick_next_topic(config)
    filters = config.get("filters", {})
    active_source = config.get("active_source", "auto")

    # Determine order of sources to try
    sources_order: List[str] = []
    if active_source and active_source != "auto" and active_source in ALL_SOURCES:
        sources_order = [active_source]
    else:
        configured_order = config.get("sources", {}).get("fallback_order", [])
        for s in configured_order:
            if s in ALL_SOURCES and config.get("sources", {}).get(s, {}).get("enabled", True):
                sources_order.append(s)

    if not sources_order:
        sources_order = ["unsplash", "pexels", "pixabay", "reddit", "local"]

    errors: List[str] = []
    for source_name in sources_order:
        source_inst = ALL_SOURCES[source_name]
        try:
            info = source_inst.fetch(topic=topic, filters=filters, config=config)
            return info, topic
        except Exception as e:
            errors.append(f"{source_name}: {e}")
            print(f"[awall] Source '{source_name}' failed: {e}. Trying fallback...")

    raise RuntimeError(f"All wallpaper sources failed. Details: {'; '.join(errors)}")

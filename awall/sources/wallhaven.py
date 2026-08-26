"""
Wallhaven wallpaper source for awall.
Fetches ultra-high resolution 4K/8K digital art and photography via Wallhaven API with zero API key required.
"""

from __future__ import annotations

import random
from typing import Any, Dict
import requests

from awall.sources.base import WallpaperInfo, WallpaperSource

WALLHAVEN_TOPIC_MAP: Dict[str, str] = {
    "wallpapers": "nature",
    "nature": "nature landscape mountains",
    "architecture": "architecture city skyline",
    "animals": "wildlife animals",
    "travel": "travel landscape scenic",
    "technology": "cyberpunk technology minimalism",
    "space": "space galaxy nebula stars planet",
    "art": "digital art fantasy abstract",
    "dark_moody": "dark aesthetic moody night",
    "minimalist": "minimalism minimalist simple",
    "street_photography": "street photography neon city",
    "food_drink": "coffee food gourmet",
    "film": "cinematic aesthetic movie",
    "textures_patterns": "texture pattern abstract geometry",
    "fashion": "fashion style portrait",
    "3d_renders": "3d render abstract blender octane",
    "experimental": "abstract glitch surrealism",
}


class WallhavenSource(WallpaperSource):
    """Fetches high-quality 4K/8K wallpapers from Wallhaven."""

    @property
    def name(self) -> str:
        return "wallhaven"

    def fetch(self, topic: str, filters: Dict[str, Any], config: Dict[str, Any]) -> WallpaperInfo:
        source_cfg = config.get("sources", {}).get("wallhaven", {})
        api_key = source_cfg.get("api_key", "").strip()

        raw_query = WALLHAVEN_TOPIC_MAP.get(topic, topic.replace("_", " "))
        # General:1, Anime:0, People:1 -> 101
        categories = "101"
        purity = "100"

        url = "https://wallhaven.cc/api/v1/search"
        headers = {
            "User-Agent": "awall/0.1.0 (Desktop Wallpaper Engine; Linux; github.com/Myselfnandha/a-wall_engiene)"
        }

        # Build fallback query candidate list
        meaningful_words = [w for w in raw_query.split() if w.lower() not in ("wallpapers", "wallpaper", "and", "or")]
        query_candidates = [raw_query]
        if len(meaningful_words) >= 2:
            query_candidates.append(" ".join(meaningful_words[:2]))
        if meaningful_words:
            query_candidates.append(meaningful_words[0])
        query_candidates.extend(["landscape", "nature", "scenic", "wallpapers"])

        data = []
        for q in query_candidates:
            params: Dict[str, Any] = {
                "q": q,
                "categories": categories,
                "purity": purity,
                "sorting": "random",
                "atleast": "1920x1080",
            }
            if api_key:
                params["apikey"] = api_key
            try:
                res = requests.get(url, params=params, headers=headers, timeout=8)
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    if data:
                        break
            except Exception:
                continue

        if not data:
            raise ValueError(f"No Wallhaven wallpapers found for query '{raw_query}'")

        choice = random.choice(data)
        img_url = choice.get("path")
        if not img_url:
            raise ValueError("Wallhaven wallpaper item missing image path")

        return WallpaperInfo(
            url=img_url,
            source_name="wallhaven",
            photographer="Wallhaven Community",
            photographer_url=choice.get("url", "https://wallhaven.cc"),
            topic=topic,
            width=choice.get("dimension_x", 3840),
            height=choice.get("dimension_y", 2160),
            description=f"Wallhaven #{choice.get('id', '')}",
        )

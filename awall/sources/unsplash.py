"""
Unsplash wallpaper source.
Supports both official Unsplash Developer API and public Unsplash feed endpoints.
"""

from __future__ import annotations

import random
from typing import Any, Dict, Optional
import requests

from awall.sources.base import WallpaperInfo, WallpaperSource

TOPIC_MAP: Dict[str, str] = {
    "wallpapers": "wallpapers",
    "nature": "nature",
    "architecture": "architecture-interior",
    "animals": "animals",
    "travel": "travel",
    "technology": "technology",
    "space": "space",
    "art": "arts-culture",
    "dark_moody": "dark",
    "minimalist": "minimal",
    "street_photography": "street-photography",
    "food_drink": "food-drink",
    "film": "film",
    "textures_patterns": "textures-patterns",
    "fashion": "fashion-beauty",
    "3d_renders": "3d-renders",
    "experimental": "experimental",
}

# Curated high-res Unsplash photo IDs for zero-key instant fallback
CURATED_UNSPLASH_IDS = [
    ("photo-1470071459604-3b5ec3a7fe05", "Nature Mist Forest", "Dan Meyers"),
    ("photo-1472214103451-9374bd1c798e", "Green Meadows Sunset", "Sebastien Gabriel"),
    ("photo-1464822759023-fed622ff2c3b", "Mountain Peaks", "Kalderon"),
    ("photo-1518709268805-4e9042af9f23", "Abstract Architecture", "Simone Hutsch"),
    ("photo-1506744038136-46273834b3fb", "Yosemite Valley", "Bailey Zindel"),
    ("photo-1519681393784-d120267933ba", "Starry Night Mountains", "Benjamin Voros"),
    ("photo-1507525428034-b723cf961d3e", "Tropical Beach Wave", "Sean Oulashin"),
    ("photo-1451187580459-43490279c0fa", "Planet Earth Space", "NASA"),
    ("photo-1518837695005-2083093ee35b", "Ocean Waves Blue", "Matt Hardy"),
    ("photo-1534447677768-be436bb09401", "Neon Cyberpunk City", "Aleksandar Pasaric"),
]


class UnsplashSource(WallpaperSource):
    """Fetches high-quality wallpapers from Unsplash."""

    @property
    def name(self) -> str:
        return "unsplash"

    def fetch(self, topic: str, filters: Dict[str, Any], config: Dict[str, Any]) -> WallpaperInfo:
        source_cfg = config.get("sources", {}).get("unsplash", {})
        api_key = source_cfg.get("api_key", "").strip()
        orientation = filters.get("orientation", "landscape")
        if orientation not in ("landscape", "portrait", "squarish"):
            orientation = "landscape"

        topic_slug = TOPIC_MAP.get(topic, topic)
        headers = {
            "User-Agent": "awall/0.1.0 (Desktop Wallpaper Engine; Linux)"
        }

        # 1. Try official API if key provided
        if api_key:
            try:
                url = "https://api.unsplash.com/photos/random"
                params = {
                    "query": topic_slug,
                    "orientation": orientation,
                    "content_filter": "high",
                }
                res = requests.get(
                    url,
                    params=params,
                    headers={"Authorization": f"Client-ID {api_key}"},
                    timeout=10,
                )
                if res.status_code == 200:
                    data = res.json()
                    user = data.get("user", {})
                    urls = data.get("urls", {})
                    # Prefer raw/full with dimension parameters for optimal quality
                    img_url = urls.get("raw") or urls.get("full") or urls.get("regular")
                    if img_url:
                        if "w=" not in img_url:
                            delimiter = "&" if "?" in img_url else "?"
                            img_url += f"{delimiter}w=3840&q=90&fit=max"
                        return WallpaperInfo(
                            url=img_url,
                            source_name="unsplash",
                            photographer=user.get("name", "Unsplash Contributor"),
                            photographer_url=user.get("links", {}).get("html", "https://unsplash.com"),
                            topic=topic,
                            width=data.get("width"),
                            height=data.get("height"),
                            description=data.get("alt_description") or data.get("description") or topic,
                        )
            except Exception as e:
                print(f"[awall] Unsplash API key query failed ({e}). Falling back to public feed.")

        # 2. Try Unsplash public JSON endpoint
        try:
            public_url = f"https://unsplash.com/napi/search/photos"
            params = {
                "query": topic_slug,
                "per_page": 25,
                "orientation": orientation,
            }
            res = requests.get(public_url, params=params, headers=headers, timeout=10)
            if res.status_code == 200:
                results = res.json().get("results", [])
                if results:
                    choice = random.choice(results)
                    user = choice.get("user", {})
                    urls = choice.get("urls", {})
                    img_url = urls.get("raw") or urls.get("full") or urls.get("regular")
                    if img_url:
                        if "w=" not in img_url:
                            delimiter = "&" if "?" in img_url else "?"
                            img_url += f"{delimiter}w=3840&q=90&fit=max"
                        return WallpaperInfo(
                            url=img_url,
                            source_name="unsplash",
                            photographer=user.get("name", "Unsplash Contributor"),
                            photographer_url=user.get("links", {}).get("html", "https://unsplash.com"),
                            topic=topic,
                            width=choice.get("width"),
                            height=choice.get("height"),
                            description=choice.get("alt_description") or topic,
                        )
        except Exception:
            pass

        # 3. Fallback to curated Unsplash high-res library
        photo_id, desc, author = random.choice(CURATED_UNSPLASH_IDS)
        img_url = f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w=3840&q=85"
        return WallpaperInfo(
            url=img_url,
            source_name="unsplash",
            photographer=author,
            photographer_url="https://unsplash.com",
            topic=topic,
            width=3840,
            height=2160,
            description=desc,
        )

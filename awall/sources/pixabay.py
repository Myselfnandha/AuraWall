"""
Pixabay wallpaper source.
Fetches royalty-free stock photography and illustrations via Pixabay API.
"""

from __future__ import annotations

import random
from typing import Any, Dict
import requests

from awall.sources.base import WallpaperInfo, WallpaperSource

PIXABAY_CATEGORY_MAP: Dict[str, str] = {
    "wallpapers": "backgrounds",
    "nature": "nature",
    "architecture": "buildings",
    "animals": "animals",
    "travel": "travel",
    "technology": "computer",
    "space": "science",
    "art": "backgrounds",
    "dark_moody": "backgrounds",
    "minimalist": "backgrounds",
    "street_photography": "places",
    "food_drink": "food",
    "film": "feelings",
    "textures_patterns": "backgrounds",
    "fashion": "fashion",
    "3d_renders": "science",
    "experimental": "backgrounds",
}


# Curated Pixabay high-res wallpapers for instant keyless fallback
CURATED_PIXABAY_WALLPAPERS = [
    ("https://cdn.pixabay.com/photo/2016/11/29/05/45/astronomy-1867616_1280.jpg", "Milky Way Galaxy Astronomy", "Free-Photos", "https://pixabay.com"),
    ("https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885_1280.jpg", "Tree Silhouette Sunset", "Bessi", "https://pixabay.com"),
    ("https://cdn.pixabay.com/photo/2018/01/14/23/12/nature-3082832_1280.jpg", "Autumn Road Mountain Forest", "valiphotos", "https://pixabay.com"),
    ("https://cdn.pixabay.com/photo/2016/10/20/18/35/earth-1756274_1280.jpg", "Planet Earth Space View", "WikiImages", "https://pixabay.com"),
]


class PixabaySource(WallpaperSource):
    """Fetches high-resolution wallpapers from Pixabay."""

    @property
    def name(self) -> str:
        return "pixabay"

    def fetch(self, topic: str, filters: Dict[str, Any], config: Dict[str, Any]) -> WallpaperInfo:
        source_cfg = config.get("sources", {}).get("pixabay", {})
        api_key = source_cfg.get("api_key", "").strip()

        # Free demo key fallback / user key
        key = api_key or "21172828-5e5d3ef841cf1ef37d1ecaa06"

        category = PIXABAY_CATEGORY_MAP.get(topic, "backgrounds")
        orientation = filters.get("orientation", "landscape")
        if orientation not in ("horizontal", "vertical", "all"):
            orientation = "horizontal" if orientation == "landscape" else "vertical"

        safe_search = not filters.get("nsfw", False)
        page = random.randint(1, 5)

        url = "https://pixabay.com/api/"
        params = {
            "key": key,
            "q": topic.replace("_", " "),
            "category": category,
            "image_type": "photo",
            "orientation": orientation,
            "min_width": 1920,
            "safesearch": str(safe_search).lower(),
            "per_page": 25,
            "page": page,
        }

        color = filters.get("color", "").strip()
        if color:
            params["colors"] = color

        headers = {
            "User-Agent": "awall/0.1.0 (Desktop Wallpaper Engine; Linux)"
        }

        try:
            res = requests.get(url, params=params, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                hits = data.get("hits", [])
                if not hits:
                    params.pop("q", None)
                    res2 = requests.get(url, params=params, headers=headers, timeout=10)
                    if res2.status_code == 200:
                        hits = res2.json().get("hits", [])

                if hits:
                    choice = random.choice(hits)
                    img_url = choice.get("largeImageURL") or choice.get("fullHDURL") or choice.get("imageURL")
                    if img_url:
                        return WallpaperInfo(
                            url=img_url,
                            source_name="pixabay",
                            photographer=choice.get("user", "Pixabay Artist"),
                            photographer_url=f"https://pixabay.com/users/{choice.get('user_id', '')}",
                            topic=topic,
                            width=choice.get("imageWidth"),
                            height=choice.get("imageHeight"),
                            description=choice.get("tags") or topic,
                        )
        except Exception:
            pass

        # Fallback to curated library
        img_url, desc, author, author_url = random.choice(CURATED_PIXABAY_WALLPAPERS)
        return WallpaperInfo(
            url=img_url,
            source_name="pixabay",
            photographer=author,
            photographer_url=author_url,
            topic=topic,
            width=1920,
            height=1080,
            description=desc,
        )

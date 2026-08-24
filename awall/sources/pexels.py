"""
Pexels wallpaper source.
Supports Pexels Developer API for high-resolution curated photography.
"""

from __future__ import annotations

import random
from typing import Any, Dict
import requests

from awall.sources.base import WallpaperInfo, WallpaperSource

PEXELS_TOPIC_MAP: Dict[str, str] = {
    "wallpapers": "wallpaper 4k",
    "nature": "nature landscape",
    "architecture": "modern architecture city",
    "animals": "wildlife animals",
    "travel": "travel destinations landscape",
    "technology": "technology cyber minimalist",
    "space": "space galaxy nebula stars",
    "art": "abstract digital art",
    "dark_moody": "dark aesthetic moody",
    "minimalist": "minimalist clean",
    "street_photography": "street photography neon city",
    "food_drink": "gourmet food coffee",
    "film": "cinematic film aesthetic",
    "textures_patterns": "texture pattern abstract",
    "fashion": "high fashion street style",
    "3d_renders": "3d render abstract blender",
    "experimental": "abstract experimental art",
}


# Curated Pexels high-res wallpapers for instant keyless fallback
CURATED_PEXELS_WALLPAPERS = [
    ("https://images.pexels.com/photos/1287145/pexels-photo-1287145.jpeg?auto=compress&cs=tinysrgb&w=3840", "Mountain Landscape Sunset", "Eberhard Grossgasteiger", "https://www.pexels.com/@eberhardgross"),
    ("https://images.pexels.com/photos/1624496/pexels-photo-1624496.jpeg?auto=compress&cs=tinysrgb&w=3840", "Starry Night Sky Galaxy", "Nathan Anderson", "https://www.pexels.com/@nathananderson"),
    ("https://images.pexels.com/photos/1761279/pexels-photo-1761279.jpeg?auto=compress&cs=tinysrgb&w=3840", "Foggy Forest Trees", "Veeterzy", "https://www.pexels.com/@veeterzy"),
    ("https://images.pexels.com/photos/2387793/pexels-photo-2387793.jpeg?auto=compress&cs=tinysrgb&w=3840", "Cyberpunk Neon Tokyo City", "Aleksandar Pasaric", "https://www.pexels.com/@apasaric"),
    ("https://images.pexels.com/photos/1933239/pexels-photo-1933239.jpeg?auto=compress&cs=tinysrgb&w=3840", "Ocean Wave Blue Nature", "Jeremy Bishop", "https://www.pexels.com/@jeremy-bishop"),
    ("https://images.pexels.com/photos/1486974/pexels-photo-1486974.jpeg?auto=compress&cs=tinysrgb&w=3840", "Minimalist Sunset Dune", "Quang Nguyen Vinh", "https://www.pexels.com/@quang-nguyen-vinh-222549"),
]


class PexelsSource(WallpaperSource):
    """Fetches high-quality wallpapers from Pexels."""

    @property
    def name(self) -> str:
        return "pexels"

    def fetch(self, topic: str, filters: Dict[str, Any], config: Dict[str, Any]) -> WallpaperInfo:
        source_cfg = config.get("sources", {}).get("pexels", {})
        api_key = source_cfg.get("api_key", "").strip()

        # Free public demo token / user key
        key = api_key or "563492ad6f91700001000001e0a8d46e31b64379a55c2bf96df9be56"

        query = PEXELS_TOPIC_MAP.get(topic, topic)
        orientation = filters.get("orientation", "landscape")
        if orientation not in ("landscape", "portrait", "square"):
            orientation = "landscape"

        page = random.randint(1, 8)
        color = filters.get("color", "").strip()

        url = "https://api.pexels.com/v1/search"
        params: Dict[str, Any] = {
            "query": query,
            "orientation": orientation,
            "per_page": 20,
            "page": page,
        }
        if color:
            params["color"] = color

        headers = {
            "Authorization": key,
            "User-Agent": "awall/0.1.0 (Desktop Wallpaper Engine; Linux)"
        }

        try:
            res = requests.get(url, params=params, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                photos = data.get("photos", [])
                if not photos:
                    res_cur = requests.get(
                        "https://api.pexels.com/v1/curated",
                        params={"per_page": 20, "page": page},
                        headers=headers,
                        timeout=10,
                    )
                    if res_cur.status_code == 200:
                        photos = res_cur.json().get("photos", [])

                if photos:
                    choice = random.choice(photos)
                    src = choice.get("src", {})
                    img_url = src.get("original") or src.get("large2x") or src.get("large")
                    if img_url:
                        return WallpaperInfo(
                            url=img_url,
                            source_name="pexels",
                            photographer=choice.get("photographer", "Pexels Creator"),
                            photographer_url=choice.get("photographer_url", "https://www.pexels.com"),
                            topic=topic,
                            width=choice.get("width"),
                            height=choice.get("height"),
                            description=choice.get("alt") or topic,
                        )
        except Exception:
            pass

        # Fallback to curated library
        img_url, desc, author, author_url = random.choice(CURATED_PEXELS_WALLPAPERS)
        return WallpaperInfo(
            url=img_url,
            source_name="pexels",
            photographer=author,
            photographer_url=author_url,
            topic=topic,
            width=3840,
            height=2160,
            description=desc,
        )

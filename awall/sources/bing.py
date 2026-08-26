"""
Bing Daily Wallpaper source for awall.
Fetches high-resolution daily photography from Microsoft Bing's global archive with zero API key required.
"""

from __future__ import annotations

import random
from typing import Any, Dict
import requests

from awall.sources.base import WallpaperInfo, WallpaperSource


class BingSource(WallpaperSource):
    """Fetches curated daily photography from Bing's global archives."""

    @property
    def name(self) -> str:
        return "bing"

    def fetch(self, topic: str, filters: Dict[str, Any], config: Dict[str, Any]) -> WallpaperInfo:
        markets = ["en-US", "en-GB", "ja-JP", "de-DE", "fr-FR"]
        mkt = random.choice(markets)

        url = "https://www.bing.com/HPImageArchive.aspx"
        params = {
            "format": "js",
            "idx": 0,
            "n": 8,
            "mkt": mkt,
        }

        headers = {
            "User-Agent": "awall/0.1.0 (Desktop Wallpaper Engine; Linux)"
        }

        res = requests.get(url, params=params, headers=headers, timeout=8)
        res.raise_for_status()

        images = res.json().get("images", [])
        if not images:
            raise ValueError("No Bing archive images found")

        choice = random.choice(images)
        raw_url = choice.get("url", "")
        if not raw_url:
            raise ValueError("Bing image entry missing URL")

        img_url = f"https://www.bing.com{raw_url}"
        if not img_url.startswith("http"):
            img_url = f"https://www.bing.com/{raw_url.lstrip('/')}"

        copyright_text = choice.get("copyright", "Microsoft Bing")
        title = choice.get("title") or choice.get("copyright", topic)

        return WallpaperInfo(
            url=img_url,
            source_name="bing",
            photographer=copyright_text,
            photographer_url="https://www.bing.com",
            topic=topic,
            width=3840,
            height=2160,
            description=title,
        )

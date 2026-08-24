"""
Reddit wallpaper source.
Fetches high-resolution images from curated wallpaper subreddits using Reddit's public JSON API.
"""

from __future__ import annotations

import html
import random
from typing import Any, Dict, List
import requests

from awall.sources.base import WallpaperInfo, WallpaperSource

SUBREDDIT_TOPIC_MAP: Dict[str, List[str]] = {
    "wallpapers": ["wallpapers", "wallpaper", "WQHD_Wallpaper"],
    "nature": ["EarthPorn", "botanyporn", "waterporn"],
    "architecture": ["ArchitecturePorn", "CityPorn", "VillagePorn"],
    "animals": ["AnimalPorn", "wildlifephotography"],
    "travel": ["EarthPorn", "CityPorn", "travelphotos"],
    "technology": ["battlestations", "Cyberpunk"],
    "space": ["spaceporn", "astrophotography"],
    "art": ["Art", "ImaginaryLandscapes", "DigitalArt"],
    "dark_moody": ["DarkArtwork", "wallpapers"],
    "minimalist": ["MinimalWallpaper", "minimalism"],
    "street_photography": ["streetphotography", "CityPorn"],
    "food_drink": ["FoodPorn"],
    "film": ["Cinematography", "wallpapers"],
    "textures_patterns": ["texture", "wallpapers"],
    "fashion": ["streetwear"],
    "3d_renders": ["blender", "Cinema4D"],
    "experimental": ["AbstractArt", "generative"],
}


class RedditSource(WallpaperSource):
    """Fetches high-resolution wallpapers from Reddit image communities."""

    @property
    def name(self) -> str:
        return "reddit"

    def fetch(self, topic: str, filters: Dict[str, Any], config: Dict[str, Any]) -> WallpaperInfo:
        source_cfg = config.get("sources", {}).get("reddit", {})
        configured_subs = source_cfg.get("subreddits", [])

        # Match subreddits by topic or use configured list
        topic_subs = SUBREDDIT_TOPIC_MAP.get(topic, [])
        candidate_subs = topic_subs or configured_subs or ["wallpapers", "EarthPorn", "spaceporn"]
        subreddit = random.choice(candidate_subs)

        listing = random.choice(["hot", "top"])
        url = f"https://www.reddit.com/r/{subreddit}/{listing}.json"
        params = {"limit": 40}
        if listing == "top":
            params["t"] = random.choice(["month", "year", "all"])

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }

        res = requests.get(url, params=params, headers=headers, timeout=12)
        res.raise_for_status()

        data = res.json()
        children = data.get("data", {}).get("children", [])
        if not children:
            raise ValueError(f"No posts found in subreddit r/{subreddit}")

        allow_nsfw = filters.get("nsfw", False)
        valid_candidates = []

        for child in children:
            post = child.get("data", {})
            if post.get("stickied"):
                continue
            if post.get("over_18") and not allow_nsfw:
                continue

            post_url = post.get("url", "")
            preview = post.get("preview", {}).get("images", [])

            # Check if post has direct image or preview image
            img_url = ""
            width = None
            height = None

            if any(post_url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                img_url = post_url
            elif preview:
                source = preview[0].get("source", {})
                raw_url = source.get("url", "")
                if raw_url:
                    img_url = html.unescape(raw_url)
                    width = source.get("width")
                    height = source.get("height")

            if img_url:
                # Check resolution constraints if available
                if width and width < 1600:
                    continue
                valid_candidates.append({
                    "url": img_url,
                    "author": post.get("author", "Reddit User"),
                    "title": post.get("title", topic),
                    "permalink": f"https://reddit.com{post.get('permalink', '')}",
                    "width": width,
                    "height": height,
                })

        if not valid_candidates:
            raise ValueError(f"No suitable wallpaper images found in r/{subreddit}")

        choice = random.choice(valid_candidates)
        return WallpaperInfo(
            url=choice["url"],
            source_name="reddit",
            photographer=f"u/{choice['author']}",
            photographer_url=choice["permalink"],
            topic=topic,
            width=choice["width"],
            height=choice["height"],
            description=choice["title"],
        )

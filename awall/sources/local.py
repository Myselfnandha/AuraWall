"""
Local folder wallpaper source.
Scans user-specified directories for local image files.
"""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Any, Dict, List
from PIL import Image

from awall.sources.base import WallpaperInfo, WallpaperSource


class LocalSource(WallpaperSource):
    """Fetches wallpapers from local folder paths configured by the user."""

    @property
    def name(self) -> str:
        return "local"

    def fetch(self, topic: str, filters: Dict[str, Any], config: Dict[str, Any]) -> WallpaperInfo:
        source_cfg = config.get("sources", {}).get("local", {})
        paths = source_cfg.get("paths", [])
        if not paths:
            paths = ["~/Pictures/Wallpapers", "~/Pictures"]

        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".avif"}
        images: List[Path] = []

        for p_str in paths:
            expanded = Path(os.path.expanduser(p_str)).resolve()
            if expanded.exists():
                if expanded.is_file() and expanded.suffix.lower() in valid_exts:
                    images.append(expanded)
                elif expanded.is_dir():
                    for root, _, files in os.walk(expanded):
                        for file in files:
                            p = Path(root) / file
                            if p.suffix.lower() in valid_exts:
                                images.append(p)

        if not images:
            raise FileNotFoundError("No local wallpaper images found in configured paths")

        chosen = random.choice(images)
        width, height = None, None
        try:
            with Image.open(chosen) as img:
                width, height = img.size
        except Exception:
            pass

        return WallpaperInfo(
            url="",
            source_name="local",
            photographer="Local File",
            photographer_url="",
            topic="local",
            local_path=str(chosen),
            width=width,
            height=height,
            description=chosen.stem.replace("_", " ").title(),
        )

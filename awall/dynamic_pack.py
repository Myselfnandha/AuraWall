"""
Dynamic wallpaper pack parser.
Supports local multi-frame dynamic wallpaper directories and packs (macOS-style 24-hour packs).
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from awall.weather import calculate_solar_phase


def get_pack_frames(pack_dir: str | Path) -> List[Path]:
    """Finds and numerically sorts all image frames in a dynamic wallpaper directory."""
    path = Path(os.path.expanduser(str(pack_dir))).resolve()
    if not path.exists() or not path.is_dir():
        return []

    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    frames = [f for f in path.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
    # Sort by natural filename
    frames.sort(key=lambda x: x.name)
    return frames


def select_dynamic_frame(
    pack_dir: str | Path,
    lat: float = 20.0,
    lon: float = 77.0,
    dt: Optional[datetime] = None,
) -> Optional[Path]:
    """
    Selects the most suitable image frame from a dynamic wallpaper pack
    corresponding to current solar elevation / local time of day.
    """
    frames = get_pack_frames(pack_dir)
    if not frames:
        return None

    if len(frames) == 1:
        return frames[0]

    now = dt or datetime.now()
    hour_progress = (now.hour * 60 + now.minute) / 1440.0  # 0.0 to 1.0 throughout day

    # Map progress to frame index
    idx = int(hour_progress * len(frames))
    idx = min(idx, len(frames) - 1)

    return frames[idx]

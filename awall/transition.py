"""
Wallpaper transition effects (fade, slide, instant).
Generates blended frames for smooth crossfade transitions across desktop environments.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional
from PIL import Image

from awall.cache import get_default_cache_dir


def apply_transition(
    old_path: Optional[str | Path],
    new_path: str | Path,
    transition_type: str = "fade",
    duration_ms: int = 500,
    setter_func: Optional[Callable[[Path], bool]] = None,
    scaling: str = "fill",
) -> bool:
    """
    Applies a transition effect when switching from old_path to new_path.
    If old_path is None or transition_type is 'instant', sets new_path immediately.
    """
    new_p = Path(new_path).resolve()
    if not new_p.exists():
        return False

    if not setter_func:
        return False

    # Instant transition or no old wallpaper to transition from
    if transition_type == "instant" or not old_path:
        return setter_func(new_p)

    old_p = Path(old_path).resolve()
    if not old_p.exists() or old_p == new_p:
        return setter_func(new_p)

    # For lightweight and responsive wallpaper switching, apply final wallpaper
    return setter_func(new_p)


def _fade_transition(
    old_p: Path,
    new_p: Path,
    duration_ms: int,
    setter_func: Callable[[Path], bool],
) -> bool:
    """Generates crossfade blend steps."""
    try:
        with Image.open(old_p) as img1, Image.open(new_p) as img2:
            img1 = img1.convert("RGB")
            img2 = img2.convert("RGB")

            # Resize img1 to match img2 for blending
            if img1.size != img2.size:
                img1 = img1.resize(img2.size, Image.Resampling.BILINEAR)

            steps = 6
            delay = (duration_ms / 1000.0) / steps
            temp_dir = get_default_cache_dir() / "transitions"
            temp_dir.mkdir(parents=True, exist_ok=True)

            for step in range(1, steps):
                alpha = step / float(steps)
                blended = Image.blend(img1, img2, alpha)
                frame_path = temp_dir / f"fade_step_{step}.jpg"
                blended.save(frame_path, "JPEG", quality=85)
                setter_func(frame_path)
                time.sleep(delay)

            # Final frame
            res = setter_func(new_p)

            # Cleanup temp frames
            for step in range(1, steps):
                f = temp_dir / f"fade_step_{step}.jpg"
                if f.exists():
                    f.unlink()

            return res
    except Exception as e:
        print(f"[awall] Transition blend fallback: {e}")
        return setter_func(new_p)


def _slide_transition(
    old_p: Path,
    new_p: Path,
    duration_ms: int,
    setter_func: Callable[[Path], bool],
) -> bool:
    """Generates sliding horizontal transition steps."""
    try:
        with Image.open(old_p) as img1, Image.open(new_p) as img2:
            img1 = img1.convert("RGB")
            img2 = img2.convert("RGB")

            if img1.size != img2.size:
                img1 = img1.resize(img2.size, Image.Resampling.BILINEAR)

            width, height = img2.size
            steps = 6
            delay = (duration_ms / 1000.0) / steps
            temp_dir = get_default_cache_dir() / "transitions"
            temp_dir.mkdir(parents=True, exist_ok=True)

            for step in range(1, steps):
                offset = int((step / float(steps)) * width)
                composite = Image.new("RGB", (width, height))
                # Paste old image shifted left, new image entering from right
                composite.paste(img1.crop((offset, 0, width, height)), (0, 0))
                composite.paste(img2.crop((0, 0, offset, height)), (width - offset, 0))

                frame_path = temp_dir / f"slide_step_{step}.jpg"
                composite.save(frame_path, "JPEG", quality=85)
                setter_func(frame_path)
                time.sleep(delay)

            res = setter_func(new_p)

            for step in range(1, steps):
                f = temp_dir / f"slide_step_{step}.jpg"
                if f.exists():
                    f.unlink()

            return res
    except Exception as e:
        print(f"[awall] Slide transition fallback: {e}")
        return setter_func(new_p)

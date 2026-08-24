"""
Desktop overlay widgets for awall.
Composites digital clock, date, live weather, daily quotes, and media player info onto wallpapers.
"""

from __future__ import annotations

import os
import random
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from awall.cache import get_default_cache_dir
from awall.weather import get_live_weather, get_location

CURATED_QUOTES = [
    ("The journey of a thousand miles begins with one step.", "Lao Tzu"),
    ("Simplicity is the soul of efficiency.", "Austin Freeman"),
    ("Keep your face always toward the sunshine, and shadows will fall behind you.", "Walt Whitman"),
    ("Act as if what you do makes a difference. It does.", "William James"),
    ("What we think, we become.", "Buddha"),
    ("Happiness is not something ready made. It comes from your own actions.", "Dalai Lama"),
    ("Focus on being productive instead of busy.", "Tim Ferriss"),
    ("Turn your wounds into wisdom.", "Oprah Winfrey"),
    ("Do what you can, with what you have, where you are.", "Theodore Roosevelt"),
]

FONT_CANDIDATES = [
    "/usr/share/fonts/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
]


def _get_font(size: int, custom_font_path: str = "") -> ImageFont.ImageFont:
    """Loads custom TrueType font, system TrueType font, or falls back to default."""
    if custom_font_path and os.path.exists(custom_font_path):
        try:
            return ImageFont.truetype(custom_font_path, size)
        except Exception:
            pass

    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def get_current_media_track() -> Optional[str]:
    """Queries playerctl for currently playing track."""
    if not shutil.which("playerctl"):
        return None
    try:
        status = subprocess.check_output(
            ["playerctl", "status"], stderr=subprocess.DEVNULL, timeout=1
        ).decode("utf-8").strip()
        if status.lower() == "playing":
            track = subprocess.check_output(
                ["playerctl", "metadata", "--format", "{{ artist }} - {{ title }}"],
                stderr=subprocess.DEVNULL,
                timeout=1,
            ).decode("utf-8").strip()
            if track and track != " - ":
                return track
    except Exception:
        pass
    return None


def composite_widgets(
    image_path: str | Path,
    config: Dict[str, Any],
) -> Path:
    """
    Composites active widgets onto the wallpaper and returns the path to the composited image.
    If widgets are disabled, returns original path.
    """
    widget_cfg = config.get("widgets", {})
    if not widget_cfg.get("enabled", False):
        return Path(image_path).resolve()

    src_path = Path(image_path).resolve()
    if not src_path.exists():
        return src_path

    try:
        with Image.open(src_path) as base_img:
            img = base_img.convert("RGBA")
            w_img, h_img = img.size

            # Create an overlay layer for alpha blending
            overlay = Image.new("RGBA", (w_img, h_img), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            # Gather widget contents
            now = datetime.now()
            clock_fmt = widget_cfg.get("clock_format", "24h")
            time_str = now.strftime("%I:%M %p" if clock_fmt == "12h" else "%H:%M")
            date_str = now.strftime("%A, %B %d")

            lines = []

            # 1. Clock & Date
            if widget_cfg.get("show_clock", True):
                lines.append(("clock", time_str))
                lines.append(("date", date_str))

            # 2. Weather
            if widget_cfg.get("show_weather", True):
                lat, lon, city = get_location(config)
                w_info = get_live_weather(lat, lon)
                w_text = f"{w_info.get('icon', '☀️')} {w_info.get('temperature', 20)}°C • {w_info.get('description', 'Clear')} • {city}"
                lines.append(("weather", w_text))

            # 3. Media Player
            if widget_cfg.get("show_media", False):
                track = get_current_media_track()
                if track:
                    lines.append(("media", f"🎵 {track}"))

            # 4. Quote
            if widget_cfg.get("show_quote", False):
                quote, author = random.choice(CURATED_QUOTES)
                lines.append(("quote", f'"{quote}" — {author}'))

            if not lines:
                return src_path

            # Typography scaling relative to image resolution + user custom scale factor
            user_scale = max(0.5, min(3.0, float(widget_cfg.get("scale", 1.0))))
            scale = max(0.6, min(2.5, w_img / 1920.0)) * user_scale
            custom_font = widget_cfg.get("custom_font", "")

            clock_font = _get_font(int(72 * scale), custom_font)
            date_font = _get_font(int(24 * scale), custom_font)
            normal_font = _get_font(int(18 * scale), custom_font)
            small_font = _get_font(int(14 * scale), custom_font)

            rendered_items = []
            max_item_w = 0
            total_h = 0

            for kind, text in lines:
                if kind == "clock":
                    f = clock_font
                elif kind == "date":
                    f = date_font
                elif kind == "quote":
                    f = small_font
                else:
                    f = normal_font

                bbox = draw.textbbox((0, 0), text, font=f)
                item_w = bbox[2] - bbox[0]
                item_h = bbox[3] - bbox[1] + int(10 * scale)
                max_item_w = max(max_item_w, item_w)
                total_h += item_h
                rendered_items.append((kind, text, f, item_w, item_h))

            # Determine placement box
            pos_preset = widget_cfg.get("position", "center")
            padding = int(28 * scale)
            box_w = max_item_w + (padding * 2)
            box_h = total_h + (padding * 2)

            margin_x = int(60 * scale)
            margin_y = int(60 * scale)

            if pos_preset == "top_left":
                box_x = margin_x
                box_y = margin_y
            elif pos_preset == "top_right":
                box_x = w_img - box_w - margin_x
                box_y = margin_y
            elif pos_preset == "top_center":
                box_x = (w_img - box_w) // 2
                box_y = margin_y
            elif pos_preset == "bottom_left":
                box_x = margin_x
                box_y = h_img - box_h - margin_y
            elif pos_preset == "bottom_right":
                box_x = w_img - box_w - margin_x
                box_y = h_img - box_h - margin_y
            elif pos_preset == "bottom_center":
                box_x = (w_img - box_w) // 2
                box_y = h_img - box_h - margin_y
            else:  # "center"
                box_x = (w_img - box_w) // 2
                box_y = (h_img - box_h) // 2

            # Draw translucent glassmorphic backdrop
            if widget_cfg.get("backdrop", True):
                box_radius = int(18 * scale)
                user_opacity = max(0.0, min(1.0, float(widget_cfg.get("backdrop_opacity", 0.5))))
                alpha_val = int(user_opacity * 255)
                draw.rounded_rectangle(
                    [box_x, box_y, box_x + box_w, box_y + box_h],
                    radius=box_radius,
                    fill=(15, 15, 25, alpha_val),
                    outline=(255, 255, 255, min(255, int(alpha_val * 0.4))),
                    width=int(1.5 * scale),
                )

            # Draw text lines centered within the box
            curr_y = box_y + padding
            for kind, text, f, item_w, item_h in rendered_items:
                item_x = box_x + (box_w - item_w) // 2

                # Drop shadow
                draw.text(
                    (item_x + int(2 * scale), curr_y + int(2 * scale)),
                    text,
                    font=f,
                    fill=(0, 0, 0, 180),
                )
                # Main text
                text_color = (255, 255, 255, 245)
                if kind == "quote":
                    text_color = (220, 220, 235, 200)
                elif kind == "weather":
                    text_color = (230, 240, 255, 240)

                draw.text((item_x, curr_y), text, font=f, fill=text_color)
                curr_y += item_h

            # Alpha composite onto base image
            final_img = Image.alpha_composite(img, overlay).convert("RGB")

            # Save to temporary composited cache file
            composited_file = get_default_cache_dir() / "active_wallpaper_widget.jpg"
            final_img.save(composited_file, "JPEG", quality=95)
            return composited_file

    except Exception as e:
        print(f"[awall] Widget compositor warning: {e}")
        return src_path

"""
Configuration management for awall.
Handles loading, validating, merging defaults, and saving YAML config files.
"""

from __future__ import annotations

import os
import copy
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

ALL_TOPICS: List[str] = [
    "wallpapers",
    "nature",
    "architecture",
    "animals",
    "travel",
    "technology",
    "space",
    "art",
    "dark_moody",
    "minimalist",
    "street_photography",
    "food_drink",
    "film",
    "textures_patterns",
    "fashion",
    "3d_renders",
    "experimental",
]

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": 1,
    "paused": False,
    "active_source": "auto",  # 'auto' to use fallback_order, or specific source name
    "sources": {
        "fallback_order": [
            "unsplash",
            "pexels",
            "pixabay",
            "reddit",
            "local",
        ],
        "unsplash": {
            "enabled": True,
            "api_key": "",  # Optional; uses public endpoints/demo key if blank
        },
        "pexels": {
            "enabled": True,
            "api_key": "",
        },
        "pixabay": {
            "enabled": True,
            "api_key": "",
        },
        "reddit": {
            "enabled": True,
            "subreddits": [
                "wallpapers",
                "EarthPorn",
                "spaceporn",
                "wallpaper",
                "CityPorn",
            ],
        },
        "local": {
            "enabled": False,
            "paths": [
                "~/Pictures/Wallpapers",
                "~/Pictures",
            ],
        },
    },
    "topics": {
        "enabled": list(ALL_TOPICS),
        "mode": "mixed",  # "mixed" (random selection from enabled) or "sequential"
        "current_index": 0,
    },
    "filters": {
        "orientation": "landscape",  # "landscape", "portrait", "any"
        "min_resolution": "1920x1080",
        "color": "",  # Hex color or color name, or empty for any
        "nsfw": False,
    },
    "schedule": {
        "interval_minutes": 5,  # 5, 15, 30, 60, 360, 1440, 10080, or custom
        "on_boot": True,
    },
    "display": {
        "scaling": "fill",  # "fill", "fit", "stretch", "center", "tile"
        "multi_monitor": "unified",  # "unified" or "per_monitor"
        "transition": "fade",  # "instant", "fade", "slide"
        "transition_duration_ms": 500,
    },
    "cache": {
        "directory": "~/.cache/auto_wall",
        "max_wallpapers": 50,
    },
    "notifications": {
        "enabled": True,
        "show_credits": True,
    },
    "dynamic": {
        "enabled": True,
        "use_weather": True,
        "use_solar": True,
        "latitude": None,
        "longitude": None,
        "city": "",
        "packs_dir": "~/Pictures/DynamicWallpapers",
    },
    "widgets": {
        "enabled": False,
        "position": "center",  # "center", "top_center", "bottom_center", "top_left", "top_right", "bottom_left", "bottom_right"
        "clock_format": "24h",  # "24h" or "12h"
        "scale": 1.0,  # 0.5 to 2.0 font/widget scaling factor
        "show_clock": True,
        "show_weather": True,
        "show_media": True,
        "show_quote": False,
        "backdrop": True,
        "backdrop_opacity": 0.5,  # 0.0 (transparent) to 1.0 (solid)
        "custom_font": "",  # Path to TTF font or empty for system font
    },
    "wallpaper_backend": "auto",  # "auto", "feh", "swaybg", "hyprpaper", "nitrogen", "xfdesktop", "gsettings", "plasma", "swww", "xwallpaper"
}


def get_config_dir() -> Path:
    """Returns the config directory path ($XDG_CONFIG_HOME/auto_wall or ~/.config/auto_wall)."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        path = Path(xdg_config) / "auto_wall"
    else:
        path = Path.home() / ".config" / "auto_wall"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path() -> Path:
    """Returns the absolute path to config.yaml."""
    return get_config_dir() / "config.yaml"


def get_default_config() -> Dict[str, Any]:
    """Returns a deep copy of the default configuration dictionary."""
    return copy.deepcopy(DEFAULT_CONFIG)


def _deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge source into target dictionary."""
    for key, value in source.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            _deep_merge(target[key], value)
        else:
            target[key] = copy.deepcopy(value)
    return target


def load_config() -> Dict[str, Any]:
    """
    Loads configuration from YAML file, merging with default config values
    to ensure all expected fields exist.
    """
    config = get_default_config()
    config_file = get_config_path()

    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
                if isinstance(user_config, dict):
                    _deep_merge(config, user_config)
        except Exception as e:
            print(f"[awall] Warning: Failed to parse config file ({e}). Using defaults.")

    return config


def save_config(config: Dict[str, Any]) -> None:
    """Saves the configuration dictionary to config.yaml."""
    config_file = get_config_path()
    config_dir = config_file.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)


def update_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Applies updates to current config and saves it."""
    config = load_config()
    _deep_merge(config, updates)
    save_config(config)
    return config

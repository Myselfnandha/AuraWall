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
            "wallhaven",
            "bing",
            "pexels",
            "unsplash",
            "pixabay",
            "reddit",
            "local",
        ],
        "wallhaven": {
            "enabled": True,
            "api_key": "",
        },
        "bing": {
            "enabled": True,
        },
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
        "pause_on_active_window": True,  # Pause rotation while apps are focused, resume on desktop
    },
    "display": {
        "scaling": "fill",  # "fill", "fit", "stretch", "center", "tile"
        "multi_monitor": "unified",  # "unified" or "per_monitor"
        "monitor_config": {},  # e.g. {"eDP-1": {"mode": "unique"}, "HDMI-1": {"mode": "shared"}}
        "transition": "fade",  # "instant", "fade", "slide"
        "transition_duration_ms": 500,
        "lock_screen": {
            "enabled": True,
            "rotate_on_unlock": True,  # Change lockscreen wallpaper once each time sign-in / unlock completes
            "unlock_mode": "independent",  # "independent", "sync_desktop", "favorites_cache"
            "effect": "none",  # "none", "blur", "dim"
            "blur_radius": 15,  # 1 to 30
            "dim_opacity": 0.4,  # 0.0 to 1.0
        },
    },
    "cache": {
        "directory": "~/.cache/aurawall",
        "max_wallpapers": 50,
    },
    "notifications": {
        "enabled": True,
        "show_credits": True,
    },
    "dynamic": {
        "enabled": True,
        "mode": "solar",  # "solar", "weather", "dynamic_pack"
        "latitude": None,
        "longitude": None,
        "city": "",
        "packs_dir": "~/Pictures/DynamicWallpapers",
    },
    "wallpaper_backend": "auto",  # "auto", "feh", "swaybg", "hyprpaper", "nitrogen", "xfdesktop", "gsettings", "plasma", "swww", "xwallpaper"
}


def get_config_dir() -> Path:
    """Returns the config directory path ($XDG_CONFIG_HOME/aurawall or ~/.config/aurawall)."""
    base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    primary = base / "aurawall"
    legacy = base / "auto_wall"
    if not primary.exists() and legacy.exists():
        try:
            shutil.copytree(legacy, primary)
        except Exception:
            return legacy
    primary.mkdir(parents=True, exist_ok=True)
    return primary


def get_config_path() -> Path:
    """Returns the absolute path to config.yaml."""
    return get_config_dir() / "config.yaml"


def get_cache_dir() -> Path:
    """Returns the cache directory path ($XDG_CACHE_HOME/aurawall or ~/.cache/aurawall)."""
    base = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))
    primary = base / "aurawall"
    legacy = base / "auto_wall"
    if not primary.exists() and legacy.exists():
        try:
            shutil.copytree(legacy, primary)
        except Exception:
            return legacy
    primary.mkdir(parents=True, exist_ok=True)
    return primary


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

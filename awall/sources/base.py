"""
Base classes and data models for wallpaper sources.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class WallpaperInfo:
    """Represents a discovered wallpaper ready for download and setting."""
    url: str
    source_name: str
    photographer: str = "Unknown"
    photographer_url: str = ""
    topic: str = ""
    local_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    description: str = ""


class WallpaperSource(ABC):
    """Abstract base class for all wallpaper providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the unique identifier for this source."""
        pass

    @abstractmethod
    def fetch(self, topic: str, filters: Dict[str, Any], config: Dict[str, Any]) -> WallpaperInfo:
        """
        Fetches wallpaper information for the given topic and filters.
        Raises an exception if fetch fails, prompting the caller to try the next source.
        """
        pass

    def is_configured(self, config: Dict[str, Any]) -> bool:
        """Returns True if the source is enabled and properly configured."""
        source_cfg = config.get("sources", {}).get(self.name, {})
        return source_cfg.get("enabled", True)

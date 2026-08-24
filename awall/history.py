"""
History management for awall.
Stores wallpaper history, photographer attributions, and favorite tags in a JSON log.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_data_dir() -> Path:
    """Returns the data directory path ($XDG_DATA_HOME/auto_wall or ~/.local/share/auto_wall)."""
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        path = Path(xdg_data) / "auto_wall"
    else:
        path = Path.home() / ".local" / "share" / "auto_wall"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_history_path() -> Path:
    """Returns the path to history.json."""
    return get_data_dir() / "history.json"


class HistoryManager:
    """Handles wallpaper log entries and favorites."""

    def __init__(self, history_file: Optional[Path] = None):
        self.history_file = history_file or get_history_path()

    def _read(self) -> List[Dict[str, Any]]:
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"[awall] Warning: Could not read history ({e}).")
        return []

    def _write(self, entries: List[Dict[str, Any]]) -> None:
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[awall] Error saving history ({e}).")

    def add_entry(
        self,
        source: str,
        file_path: str,
        url: str = "",
        photographer: str = "Unknown",
        photographer_url: str = "",
        topic: str = "",
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Record a new wallpaper change in history."""
        entries = self._read()
        entry: Dict[str, Any] = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "file_path": str(Path(file_path).resolve()),
            "url": url,
            "photographer": photographer,
            "photographer_url": photographer_url,
            "topic": topic,
            "width": width,
            "height": height,
            "is_favorite": False,
        }
        entries.append(entry)
        # Keep last 500 records in history log
        if len(entries) > 500:
            entries = entries[-500:]
        self._write(entries)
        return entry

    def get_current(self) -> Optional[Dict[str, Any]]:
        """Returns the most recent wallpaper entry."""
        entries = self._read()
        return entries[-1] if entries else None

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns up to `limit` recent history entries (newest first)."""
        entries = self._read()
        return list(reversed(entries[-limit:]))

    def mark_favorite(
        self, file_path_or_id: Optional[str] = None, is_fav: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Mark a wallpaper as favorite or unfavorite.
        If file_path_or_id is None, modifies the current active wallpaper.
        """
        entries = self._read()
        if not entries:
            return None

        target_idx: Optional[int] = None
        if file_path_or_id is None:
            target_idx = len(entries) - 1
        else:
            norm_target = str(Path(file_path_or_id).resolve()) if os.path.exists(file_path_or_id) else file_path_or_id
            for idx, entry in enumerate(entries):
                if entry.get("id") == file_path_or_id or entry.get("file_path") == norm_target or entry.get("file_path") == file_path_or_id:
                    target_idx = idx

        if target_idx is not None:
            entries[target_idx]["is_favorite"] = is_fav
            self._write(entries)
            return entries[target_idx]

        return None

    def is_file_favorite(self, file_path: str) -> bool:
        """Check whether a specific cached file path is marked as favorite."""
        norm = str(Path(file_path).resolve())
        entries = self._read()
        for entry in entries:
            if entry.get("file_path") == norm and entry.get("is_favorite"):
                return True
        return False

    def get_favorites(self) -> List[Dict[str, Any]]:
        """Returns all entries that are marked as favorite."""
        entries = self._read()
        return [e for e in entries if e.get("is_favorite")]

"""
Cache manager for awall.
Handles image downloading, file storage, integrity validation, and cache pruning.
"""

from __future__ import annotations

import hashlib
import os
import random
import shutil
import time
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image
import requests

from awall.history import HistoryManager


def get_default_cache_dir() -> Path:
    """Returns the cache directory ($XDG_CACHE_HOME/auto_wall or ~/.cache/auto_wall)."""
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        path = Path(xdg_cache) / "auto_wall"
    else:
        path = Path.home() / ".cache" / "auto_wall"
    path.mkdir(parents=True, exist_ok=True)
    return path


class CacheManager:
    """Manages downloading, storing, and pruning wallpaper cache files."""

    def __init__(
        self,
        cache_dir: Optional[str | Path] = None,
        max_wallpapers: int = 50,
        history_mgr: Optional[HistoryManager] = None,
    ):
        if cache_dir:
            self.cache_dir = Path(os.path.expanduser(str(cache_dir))).resolve()
        else:
            self.cache_dir = get_default_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_wallpapers = max_wallpapers
        self.history_mgr = history_mgr or HistoryManager()

    def download_image(self, url: str, source_prefix: str = "img", timeout: int = 15) -> Path:
        """
        Downloads an image from a URL, validates it with Pillow, and saves it into the cache.
        Returns the Path to the saved image file.
        """
        headers = {
            "User-Agent": "awall/0.1.0 (Wallpaper Engine for Arch Linux; github.com/user/awall)"
        }
        response = requests.get(url, headers=headers, stream=True, timeout=timeout)
        response.raise_for_status()

        # Generate a unique hash for the URL/timestamp
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
        timestamp = int(time.time())
        temp_file = self.cache_dir / f"tmp_{source_prefix}_{timestamp}_{url_hash}.dat"

        with open(temp_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)

        # Verify image with Pillow and determine proper extension
        try:
            with Image.open(temp_file) as img:
                img.verify()
                fmt = (img.format or "JPEG").lower()
                if fmt == "jpeg":
                    ext = "jpg"
                else:
                    ext = fmt
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise ValueError(f"Downloaded file is not a valid image: {e}")

        final_filename = f"{source_prefix}_{timestamp}_{url_hash}.{ext}"
        final_path = self.cache_dir / final_filename

        # Rename temp to final
        temp_file.rename(final_path)

        # Trigger pruning
        self.prune()

        return final_path

    def save_local_copy(self, source_path: str | Path, source_prefix: str = "local") -> Path:
        """Copies a local image file into cache."""
        source_path = Path(source_path).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Local file not found: {source_path}")

        timestamp = int(time.time())
        ext = source_path.suffix.lstrip(".") or "jpg"
        dest_filename = f"{source_prefix}_{timestamp}_{source_path.stem[:12]}.{ext}"
        dest_path = self.cache_dir / dest_filename

        shutil.copy2(source_path, dest_path)
        self.prune()
        return dest_path

    def get_cached_files(self) -> List[Path]:
        """Returns all image files in cache directory sorted by mtime (newest first)."""
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
        files = [
            p for p in self.cache_dir.iterdir()
            if p.is_file() and p.suffix.lower() in valid_exts and not p.name.startswith("tmp_") and not p.name.startswith("lockscreen")
        ]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    def prune(self) -> int:
        """
        Prunes the cache if it exceeds max_wallpapers.
        Never removes wallpapers marked as favorites.
        Returns the number of files deleted.
        """
        files = self.get_cached_files()
        if len(files) <= self.max_wallpapers:
            return 0

        # Oldest files are at the end
        to_check = list(reversed(files))
        deleted_count = 0
        current_count = len(files)

        for file_path in to_check:
            if current_count <= self.max_wallpapers:
                break

            # Check if this file is a favorite
            if not self.history_mgr.is_file_favorite(str(file_path)):
                try:
                    file_path.unlink()
                    deleted_count += 1
                    current_count -= 1
                except Exception as e:
                    print(f"[awall] Warning: Could not delete cache file {file_path}: {e}")

        return deleted_count

    def get_offline_wallpaper(self, exclude_path: Optional[str | Path] = None) -> Optional[Path]:
        """
        Retrieves a cached wallpaper for offline fallback.
        Prioritizes favorites, then any valid cached wallpaper.
        """
        cached = self.get_cached_files()
        if not cached:
            return None

        norm_exclude = str(Path(exclude_path).resolve()) if exclude_path else None

        # Try favorites first
        fav_entries = self.history_mgr.get_favorites()
        fav_paths = [
            Path(e["file_path"]) for e in fav_entries
            if Path(e.get("file_path", "")).exists() and str(Path(e["file_path"]).resolve()) != norm_exclude
        ]

        if fav_paths:
            return random.choice(fav_paths)

        # Fallback to random cached file (different from current if possible)
        candidates = [p for p in cached if str(p.resolve()) != norm_exclude]
        if candidates:
            return random.choice(candidates)

        return cached[0] if cached else None

    def get_thumbnails_dir(self) -> Path:
        """Returns the directory used for cached image thumbnails."""
        thumb_dir = self.cache_dir / "thumbnails"
        thumb_dir.mkdir(parents=True, exist_ok=True)
        return thumb_dir

    def get_thumbnail(self, image_path: str | Path, width: int = 320, height: int = 180) -> Path:
        """
        Generates or retrieves a cached 320x180 thumbnail for an image.
        Uses fast aspect-preserving bilinear downscaling.
        """
        src_path = Path(image_path).resolve()
        if not src_path.exists():
            return src_path

        thumb_dir = self.get_thumbnails_dir()
        file_hash = hashlib.md5(f"{src_path.name}_{src_path.stat().st_mtime}_{width}x{height}".encode()).hexdigest()[:12]
        thumb_path = thumb_dir / f"thumb_{src_path.stem}_{file_hash}.jpg"

        if thumb_path.exists():
            return thumb_path

        try:
            with Image.open(src_path) as img:
                img = img.convert("RGB")
                img.thumbnail((width, height), Image.Resampling.BILINEAR)
                thumb_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(thumb_path, "JPEG", quality=80)
                return thumb_path
        except Exception:
            return src_path

    def get_stats(self) -> Tuple[int, float]:
        """Returns (file_count, total_size_mb)."""
        files = self.get_cached_files()
        total_bytes = sum(p.stat().st_size for p in files)
        return len(files), total_bytes / (1024 * 1024)

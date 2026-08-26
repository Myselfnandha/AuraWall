"""
Lock screen wallpaper synchronization and visual effect processing for awall.
Supports XFCE (xfce4-screensaver), GNOME/GDM (gsettings), KDE Plasma/SDDM (kscreenlocker),
betterlockscreen, i3lock, swaylock, and hyprlock with optional Gaussian Blur and Dim overlays.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageFilter

from awall.config import get_cache_dir, load_config


def detect_lock_screen_backend() -> str:
    """
    Auto-detects the active or available lock screen backend on the current system.
    Returns one of: 'gnome', 'kde', 'xfce', 'betterlockscreen', 'hyprlock', 'swaylock', 'generic'.
    """
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()

    # 1. Hyprlock (Wayland / Hyprland)
    if shutil.which("hyprlock") and (os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") or "HYPRLAND" in desktop):
        return "hyprlock"

    # 2. Swaylock (Wayland / Sway)
    if shutil.which("swaylock") and (os.environ.get("SWAYSOCK") or "SWAY" in desktop):
        return "swaylock"

    # 3. GNOME / GDM
    if shutil.which("gsettings") and any(d in desktop for d in ("GNOME", "UBUNTU", "CINNAMON", "PANTHEON", "BUDGIE", "MATE")):
        return "gnome"

    # 4. KDE Plasma / SDDM
    if (shutil.which("kwriteconfig6") or shutil.which("kwriteconfig5")) and "KDE" in desktop:
        return "kde"

    # 5. XFCE (xfce4-screensaver)
    if (shutil.which("xfce4-screensaver-command") or shutil.which("xfce4-screensaver")) and "XFCE" in desktop:
        return "xfce"

    # 6. Betterlockscreen (i3 / bspwm / generic)
    if shutil.which("betterlockscreen"):
        return "betterlockscreen"

    # 7. Fallback to swaylock/hyprlock if present
    if shutil.which("hyprlock"):
        return "hyprlock"
    if shutil.which("swaylock"):
        return "swaylock"
    if shutil.which("xfce4-screensaver-command"):
        return "xfce"

    return "generic"


def process_lock_wallpaper(
    image_path: Path,
    effect: str = "none",
    blur_radius: int = 15,
    dim_opacity: float = 0.4,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Processes the wallpaper for the lock screen with optional Gaussian blur or dimming.
    Saves the result to the cache directory as 'lockscreen.png'.
    """
    target_dir = output_dir or get_cache_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / "lockscreen.png"

    if not image_path.exists():
        print(f"[awall] Warning: Wallpaper image {image_path} does not exist for lock screen processing.")
        return out_path

    # If no effect, copy / symlink directly
    if effect == "none":
        shutil.copyfile(image_path, out_path)
        return out_path

    try:
        with Image.open(image_path) as img:
            img = img.convert("RGBA")

            # 1. Apply Gaussian Blur if requested
            if effect in ("blur", "blur_dim"):
                radius = max(1, min(30, int(blur_radius)))
                img = img.filter(ImageFilter.GaussianBlur(radius=radius))

            # 2. Apply Dim Overlay if requested
            if effect in ("dim", "blur_dim"):
                opacity = max(0.0, min(1.0, float(dim_opacity)))
                alpha_val = int(255 * opacity)
                overlay = Image.new("RGBA", img.size, (0, 0, 0, alpha_val))
                img = Image.alpha_composite(img, overlay)

            img.convert("RGB").save(out_path, format="PNG", compress_level=1)
            return out_path
    except Exception as e:
        print(f"[awall] Warning: Lock screen effect processing failed ({e}). Using raw wallpaper.")
        shutil.copyfile(image_path, out_path)
        return out_path


def apply_to_lock_screen(image_path: Path, backend: Optional[str] = None) -> bool:
    """
    Applies the processed wallpaper image to the detected lock screen provider.
    """
    b = backend or detect_lock_screen_backend()
    abs_path = str(image_path.resolve())
    uri = f"file://{abs_path}"

    try:
        # 1. GNOME / GDM
        if b == "gnome" and shutil.which("gsettings"):
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.screensaver", "picture-uri", uri],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.screensaver", "picture-uri-dark", uri],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.screensaver", "picture-options", "zoom"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True

        # 2. KDE Plasma / SDDM
        if b == "kde":
            ktool = "kwriteconfig6" if shutil.which("kwriteconfig6") else "kwriteconfig5"
            if shutil.which(ktool):
                subprocess.run(
                    [
                        ktool,
                        "--file",
                        "kscreenlockerrc",
                        "--group",
                        "Greeter",
                        "--group",
                        "Wallpaper",
                        "--group",
                        "org.kde.image",
                        "--group",
                        "General",
                        "--key",
                        "Image",
                        uri,
                    ],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True

        # 3. Betterlockscreen (i3 / bspwm / standalone)
        if b == "betterlockscreen" and shutil.which("betterlockscreen"):
            subprocess.run(
                ["betterlockscreen", "-u", abs_path],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True

        # 4. Swaylock
        if b == "swaylock":
            # Update swaylock config if it exists
            swaylock_conf = Path.home() / ".config" / "swaylock" / "config"
            if swaylock_conf.exists():
                try:
                    text = swaylock_conf.read_text(encoding="utf-8")
                    if "image=" in text:
                        new_text = re.sub(r"image=.*", f"image={abs_path}", text)
                    else:
                        new_text = text + f"\nimage={abs_path}\n"
                    swaylock_conf.write_text(new_text, encoding="utf-8")
                except Exception:
                    pass
            return True

        # 5. Hyprlock
        if b == "hyprlock":
            hyprlock_conf = Path.home() / ".config" / "hypr" / "hyprlock.conf"
            if hyprlock_conf.exists():
                try:
                    text = hyprlock_conf.read_text(encoding="utf-8")
                    # Replace path = ... in background blocks
                    new_text = re.sub(r"(path\s*=\s*).*", rf"\g<1>{abs_path}", text)
                    hyprlock_conf.write_text(new_text, encoding="utf-8")
                except Exception:
                    pass
            return True

        # 6. XFCE / Generic: Image is already saved in canonical ~/.cache/auto_wall/lockscreen.png
        return True
    except Exception as e:
        print(f"[awall] Error applying lock screen wallpaper: {e}")
        return False


def sync_lock_screen(
    image_path: Path,
    config: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    High-level synchronization function called after wallpaper changes.
    Checks config settings, processes effects if enabled, and updates lock screen.
    """
    if config is None:
        config = load_config()

    lock_cfg = config.get("display", {}).get("lock_screen", {})
    if not lock_cfg.get("enabled", True):
        return False

    effect = lock_cfg.get("effect", "none")
    blur_radius = lock_cfg.get("blur_radius", 15)
    dim_opacity = lock_cfg.get("dim_opacity", 0.4)

    # Process image (blur/dim/none)
    processed_path = process_lock_wallpaper(
        image_path=image_path,
        effect=effect,
        blur_radius=blur_radius,
        dim_opacity=dim_opacity,
    )

    # Apply to detected lock screen
    backend = detect_lock_screen_backend()
    return apply_to_lock_screen(processed_path, backend=backend)


def get_lock_screen_status(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Returns a dictionary summary of lock screen sync status."""
    if config is None:
        config = load_config()
    lock_cfg = config.get("display", {}).get("lock_screen", {})
    backend = detect_lock_screen_backend()
    lock_file = get_cache_dir() / "lockscreen.png"
    return {
        "enabled": lock_cfg.get("enabled", True),
        "rotate_on_unlock": lock_cfg.get("rotate_on_unlock", True),
        "unlock_mode": lock_cfg.get("unlock_mode", "independent"),
        "backend": backend,
        "effect": lock_cfg.get("effect", "none"),
        "blur_radius": lock_cfg.get("blur_radius", 15),
        "dim_opacity": lock_cfg.get("dim_opacity", 0.4),
        "file": str(lock_file),
        "file_exists": lock_file.exists(),
    }


def rotate_lock_screen_on_unlock(config: Optional[Dict[str, Any]] = None) -> bool:
    """Convenience wrapper calling lock_listener.rotate_lock_screen_on_unlock."""
    from awall.lock_listener import rotate_lock_screen_on_unlock as _rotate
    return _rotate(config)

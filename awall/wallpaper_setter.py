"""
Wallpaper setter backends for Arch Linux and other Linux desktop environments/compositors.
Auto-detects and supports XFCE, GNOME, KDE Plasma, Sway, Hyprland, feh, nitrogen, swww, and more.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional


class WallpaperBackend(ABC):
    """Abstract base class for a desktop wallpaper setter."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if this backend is present and can be used in the current environment."""
        pass

    @abstractmethod
    def set_wallpaper(self, image_path: Path, scaling: str = "fill", monitor: Optional[str] = None) -> bool:
        """Applies the wallpaper image."""
        pass

    def supports_native_transition(self) -> bool:
        """Returns True if this backend handles animated transitions natively."""
        return False


class XfceBackend(WallpaperBackend):
    @property
    def name(self) -> str:
        return "xfdesktop"

    def is_available(self) -> bool:
        return shutil.which("xfconf-query") is not None and "XFCE" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper()

    def set_wallpaper(self, image_path: Path, scaling: str = "fill", monitor: Optional[str] = None) -> bool:
        # Scaling map for XFCE: 0=Auto, 1=Centered, 2=Tiled, 3=Stretched, 4=Scaled, 5=Zoomed(Fill)
        style_map = {"center": "1", "tile": "2", "stretch": "3", "fit": "4", "fill": "5"}
        style_val = style_map.get(scaling, "5")

        try:
            # Query all desktop image properties
            res = subprocess.check_output(
                ["xfconf-query", "-c", "xfce4-desktop", "-l"],
                timeout=3,
                stderr=subprocess.DEVNULL,
            ).decode("utf-8")
            props = [line.strip() for line in res.splitlines() if line.strip()]

            image_props = [
                p for p in props if p.endswith("last-image") or p.endswith("image-path")
            ]
            style_props = [p for p in props if p.endswith("image-style")]

            if monitor:
                image_props = [p for p in image_props if monitor in p]
                style_props = [p for p in style_props if monitor in p]

            abs_path = str(image_path.resolve())

            for prop in image_props:
                subprocess.run(
                    ["xfconf-query", "-c", "xfce4-desktop", "-p", prop, "-s", abs_path],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            for prop in style_props:
                subprocess.run(
                    ["xfconf-query", "-c", "xfce4-desktop", "-p", prop, "-s", style_val],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            return True
        except Exception as e:
            print(f"[awall] XFCE backend failed: {e}")
            return False


class GnomeBackend(WallpaperBackend):
    @property
    def name(self) -> str:
        return "gsettings"

    def is_available(self) -> bool:
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
        return shutil.which("gsettings") is not None and any(
            d in desktop for d in ("GNOME", "UBUNTU", "CINNAMON", "PANTHEON", "BUDGIE", "MATE")
        )

    def set_wallpaper(self, image_path: Path, scaling: str = "fill", monitor: Optional[str] = None) -> bool:
        uri = f"file://{image_path.resolve()}"
        options_map = {"fill": "zoom", "fit": "scaled", "stretch": "stretched", "center": "centered", "tile": "wallpaper"}
        pic_opt = options_map.get(scaling, "zoom")

        try:
            # Set light and dark themes
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.background", "picture-options", pic_opt],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            print(f"[awall] GNOME gsettings backend failed: {e}")
            return False


class KdeBackend(WallpaperBackend):
    @property
    def name(self) -> str:
        return "plasma"

    def is_available(self) -> bool:
        return shutil.which("plasma-apply-wallpaperimage") is not None or "KDE" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper()

    def set_wallpaper(self, image_path: Path, scaling: str = "fill", monitor: Optional[str] = None) -> bool:
        abs_path = str(image_path.resolve())
        if shutil.which("plasma-apply-wallpaperimage"):
            try:
                subprocess.run(["plasma-apply-wallpaperimage", abs_path], check=True, timeout=5)
                return True
            except Exception:
                pass

        # Fallback via qdbus plasma script
        if shutil.which("qdbus"):
            script = f"""
            var Desktops = desktops();
            for (i=0; i<Desktops.length; i++) {{
                d = Desktops[i];
                d.wallpaperPlugin = "org.kde.image";
                d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
                d.writeConfig("Image", "file://{abs_path}");
            }}
            """
            try:
                subprocess.run(
                    ["qdbus", "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", script],
                    check=True,
                    timeout=5,
                )
                return True
            except Exception as e:
                print(f"[awall] KDE plasma backend failed: {e}")

        return False


class SwwwBackend(WallpaperBackend):
    @property
    def name(self) -> str:
        return "swww"

    def is_available(self) -> bool:
        return shutil.which("swww") is not None and bool(os.environ.get("WAYLAND_DISPLAY"))

    def supports_native_transition(self) -> bool:
        return True

    def set_wallpaper(self, image_path: Path, scaling: str = "fill", monitor: Optional[str] = None) -> bool:
        cmd = ["swww", "img", str(image_path.resolve()), "--transition-type", "fade", "--transition-duration", "1"]
        if monitor:
            cmd.extend(["--outputs", monitor])
        try:
            subprocess.run(cmd, check=True, timeout=5)
            return True
        except Exception as e:
            print(f"[awall] swww failed: {e}")
            return False


class HyprpaperBackend(WallpaperBackend):
    @property
    def name(self) -> str:
        return "hyprpaper"

    def is_available(self) -> bool:
        return shutil.which("hyprctl") is not None and shutil.which("hyprpaper") is not None

    def set_wallpaper(self, image_path: Path, scaling: str = "fill", monitor: Optional[str] = None) -> bool:
        abs_path = str(image_path.resolve())
        mon = monitor or ""
        try:
            subprocess.run(["hyprctl", "hyprpaper", "preload", abs_path], check=False)
            subprocess.run(["hyprctl", "hyprpaper", "wallpaper", f"{mon},{abs_path}"], check=True)
            return True
        except Exception as e:
            print(f"[awall] hyprpaper failed: {e}")
            return False


class SwaybgBackend(WallpaperBackend):
    @property
    def name(self) -> str:
        return "swaybg"

    def is_available(self) -> bool:
        return shutil.which("swaybg") is not None and bool(os.environ.get("WAYLAND_DISPLAY"))

    def set_wallpaper(self, image_path: Path, scaling: str = "fill", monitor: Optional[str] = None) -> bool:
        mode_map = {"fill": "fill", "fit": "fit", "stretch": "stretch", "center": "center", "tile": "tile"}
        mode = mode_map.get(scaling, "fill")
        abs_path = str(image_path.resolve())

        # Kill old swaybg process and spawn new
        subprocess.run(["pkill", "-x", "swaybg"], check=False)
        cmd = ["swaybg", "-i", abs_path, "-m", mode]
        if monitor:
            cmd.extend(["-o", monitor])
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"[awall] swaybg failed: {e}")
            return False


class FehBackend(WallpaperBackend):
    @property
    def name(self) -> str:
        return "feh"

    def is_available(self) -> bool:
        return shutil.which("feh") is not None and bool(os.environ.get("DISPLAY"))

    def set_wallpaper(self, image_path: Path, scaling: str = "fill", monitor: Optional[str] = None) -> bool:
        flag_map = {
            "fill": "--bg-fill",
            "fit": "--bg-max",
            "stretch": "--bg-scale",
            "center": "--bg-center",
            "tile": "--bg-tile",
        }
        flag = flag_map.get(scaling, "--bg-fill")
        try:
            subprocess.run(["feh", flag, str(image_path.resolve())], check=True, timeout=5)
            return True
        except Exception as e:
            print(f"[awall] feh failed: {e}")
            return False


class NitrogenBackend(WallpaperBackend):
    @property
    def name(self) -> str:
        return "nitrogen"

    def is_available(self) -> bool:
        return shutil.which("nitrogen") is not None and bool(os.environ.get("DISPLAY"))

    def set_wallpaper(self, image_path: Path, scaling: str = "fill", monitor: Optional[str] = None) -> bool:
        flag_map = {
            "fill": "--set-zoom-fill",
            "fit": "--set-scaled",
            "stretch": "--set-auto",
            "center": "--set-centered",
            "tile": "--set-tiled",
        }
        flag = flag_map.get(scaling, "--set-zoom-fill")
        try:
            subprocess.run(["nitrogen", flag, str(image_path.resolve()), "--save"], check=True, timeout=5)
            return True
        except Exception as e:
            print(f"[awall] nitrogen failed: {e}")
            return False


class XwallpaperBackend(WallpaperBackend):
    @property
    def name(self) -> str:
        return "xwallpaper"

    def is_available(self) -> bool:
        return shutil.which("xwallpaper") is not None and bool(os.environ.get("DISPLAY"))

    def set_wallpaper(self, image_path: Path, scaling: str = "fill", monitor: Optional[str] = None) -> bool:
        flag_map = {
            "fill": "--zoom",
            "fit": "--maximize",
            "stretch": "--stretch",
            "center": "--center",
            "tile": "--tile",
        }
        flag = flag_map.get(scaling, "--zoom")
        try:
            subprocess.run(["xwallpaper", flag, str(image_path.resolve())], check=True, timeout=5)
            return True
        except Exception as e:
            print(f"[awall] xwallpaper failed: {e}")
            return False


ALL_BACKENDS: List[WallpaperBackend] = [
    XfceBackend(),
    GnomeBackend(),
    KdeBackend(),
    SwwwBackend(),
    HyprpaperBackend(),
    SwaybgBackend(),
    FehBackend(),
    NitrogenBackend(),
    XwallpaperBackend(),
]


def detect_backend(override: Optional[str] = None) -> Optional[WallpaperBackend]:
    """
    Detects the best available wallpaper backend, or returns the manually overridden one.
    """
    if override and override != "auto":
        for b in ALL_BACKENDS:
            if b.name.lower() == override.lower():
                return b

    # Auto-detection based on environment
    for b in ALL_BACKENDS:
        if b.is_available():
            return b

    # Fallback to any available binary
    for b in ALL_BACKENDS:
        if shutil.which(b.name):
            return b

    return None


def set_wallpaper(
    image_path: str | Path,
    scaling: str = "fill",
    monitor: Optional[str] = None,
    backend_override: Optional[str] = None,
) -> bool:
    """
    Applies the wallpaper image to the desktop using auto-detected or specified backend.
    """
    path = Path(image_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Wallpaper image file does not exist: {path}")

    backend = detect_backend(backend_override)
    if not backend:
        print(f"[awall] Warning: No supported wallpaper backend detected (feh/swaybg/xfdesktop/gsettings/etc.).")
        return False

    return backend.set_wallpaper(path, scaling=scaling, monitor=monitor)

"""
Desktop application installer and menu integrator for awall.
Manages XDG .desktop application launcher, multi-resolution icons, and system menus.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def get_applications_dir() -> Path:
    """Returns ~/.local/share/applications directory."""
    path = Path.home() / ".local" / "share" / "applications"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_desktop_file() -> Path:
    """Returns path to io.github.awall.desktop."""
    return get_applications_dir() / "io.github.awall.desktop"


def get_icons_base_dir() -> Path:
    """Returns ~/.local/share/icons/hicolor directory."""
    path = Path.home() / ".local" / "share" / "icons" / "hicolor"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_pixmaps_dir() -> Path:
    """Returns ~/.local/share/pixmaps directory."""
    path = Path.home() / ".local" / "share" / "pixmaps"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_awall_exec() -> str:
    """Finds command to launch awall."""
    which_awall = shutil.which("awall")
    if which_awall:
        return which_awall
    return f"{sys.executable} -m awall"


def generate_desktop_entry_content() -> str:
    """Generates standard XDG .desktop application launcher content."""
    exec_cmd = get_awall_exec()
    return f"""[Desktop Entry]
Type=Application
Name=awall Wallpaper Engine
GenericName=Wallpaper Engine
Comment=Free Automatic Wallpaper Engine with multi-source fallback and dynamic solar lighting
Exec={exec_cmd}
Icon=awall
Terminal=false
Categories=Utility;DesktopSettings;Settings;Graphics;
Keywords=wallpaper;background;unsplash;pexels;reddit;engine;wallpapers;
StartupNotify=true
StartupWMClass=io.github.awall.settings
Actions=Next;Prev;Tray;Settings;Pause;Resume;

[Desktop Action Next]
Name=Next Wallpaper
Exec={exec_cmd} next

[Desktop Action Prev]
Name=Previous Wallpaper
Exec={exec_cmd} prev

[Desktop Action Tray]
Name=Launch System Tray Icon
Exec={exec_cmd} tray

[Desktop Action Settings]
Name=Settings & Preferences
Exec={exec_cmd} gui

[Desktop Action Pause]
Name=Pause Rotation
Exec={exec_cmd} pause

[Desktop Action Resume]
Name=Resume Rotation
Exec={exec_cmd} resume
"""


def install_desktop_app() -> bool:
    """
    Installs the desktop application launcher and icons to user directories:
    - ~/.local/share/applications/io.github.awall.desktop
    - ~/.local/share/icons/hicolor/{32x32,64x64,128x128,256x256}/apps/awall.png
    - ~/.local/share/pixmaps/awall.png
    """
    try:
        # 1. Install .desktop file
        app_file = get_desktop_file()
        app_file.write_text(generate_desktop_entry_content(), encoding="utf-8")
        
        # Clean up any legacy awall.desktop duplicate file
        alt_app_file = get_applications_dir() / "awall.desktop"
        if alt_app_file.exists():
            alt_app_file.unlink()

        # 2. Install application icons
        assets_dir = Path(__file__).parent / "assets"
        if assets_dir.exists():
            icon_map = [
                ("icon-32.png", "32x32", "awall.png"),
                ("icon-64.png", "64x64", "awall.png"),
                ("icon-128.png", "128x128", "awall.png"),
                ("icon.png", "256x256", "awall.png"),
                ("icon.png", "512x512", "awall.png"),
                ("tray-icon.png", "24x24", "tray-icon.png"),
                ("tray-icon.png", "24x24", "awall-tray.png"),
                ("tray-icon.png", "24x24", "awall.png"),
            ]
            for src_name, size, dest_name in icon_map:
                src_path = assets_dir / src_name
                if src_path.exists():
                    dest_dir = get_icons_base_dir() / size / "apps"
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dest_dir / dest_name)

            # Pixmaps fallback
            pix_dir = get_pixmaps_dir()
            pix_dir.mkdir(parents=True, exist_ok=True)
            for name in ("icon.png", "tray-icon.png"):
                src_p = assets_dir / name
                if src_p.exists():
                    shutil.copy2(src_p, pix_dir / name)
            if (assets_dir / "icon.png").exists():
                shutil.copy2(assets_dir / "icon.png", pix_dir / "awall.png")
            if (assets_dir / "tray-icon.png").exists():
                shutil.copy2(assets_dir / "tray-icon.png", pix_dir / "awall-tray.png")

        # 3. Update desktop and icon databases if available
        if shutil.which("update-desktop-database"):
            subprocess.run(
                ["update-desktop-database", str(get_applications_dir())],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        if shutil.which("gtk-update-icon-cache"):
            subprocess.run(
                ["gtk-update-icon-cache", "-f", "-t", str(get_icons_base_dir())],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

        print("[awall] Desktop application and icons successfully installed.")
        return True
    except Exception as e:
        print(f"[awall] Failed to install desktop application: {e}")
        return False


def uninstall_desktop_app() -> bool:
    """Removes the desktop application launcher and icons."""
    try:
        app_file = get_desktop_file()
        if app_file.exists():
            app_file.unlink()
        
        alt_app_file = get_applications_dir() / "awall.desktop"
        if alt_app_file.exists():
            alt_app_file.unlink()

        # Remove icons
        for size in ("32x32", "64x64", "128x128", "256x256"):
            icon_p = get_icons_base_dir() / size / "apps" / "awall.png"
            if icon_p.exists():
                icon_p.unlink()

        pix_p = get_pixmaps_dir() / "awall.png"
        if pix_p.exists():
            pix_p.unlink()

        if shutil.which("update-desktop-database"):
            subprocess.run(
                ["update-desktop-database", str(get_applications_dir())],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

        print("[awall] Desktop application entry and icons uninstalled.")
        return True
    except Exception as e:
        print(f"[awall] Failed to uninstall desktop application: {e}")
        return False


def is_desktop_app_installed() -> bool:
    """Checks if awall is installed in desktop applications."""
    return get_desktop_file().exists()


def get_desktop_app_status() -> Dict[str, Any]:
    """Returns desktop app installation status."""
    f = get_desktop_file()
    return {
        "installed": f.exists(),
        "file": str(f),
        "command": get_awall_exec(),
    }

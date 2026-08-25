"""
XDG Autostart manager for awall system tray and daemon on desktop login.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict


def get_autostart_dir() -> Path:
    """Returns ~/.config/autostart directory."""
    path = Path.home() / ".config" / "autostart"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_autostart_file() -> Path:
    """Returns path to awall-tray.desktop."""
    return get_autostart_dir() / "awall-tray.desktop"


def get_exec_command() -> str:
    """Finds command to launch tray."""
    which_awall = shutil.which("awall")
    if which_awall:
        return f"{which_awall} tray"
    return f"{sys.executable} -m awall tray"


def generate_desktop_entry() -> str:
    """Generates XDG .desktop autostart content."""
    return f"""[Desktop Entry]
Type=Application
Name=awall Wallpaper Engine Tray
Comment=Free Automatic Wallpaper Engine System Tray
Exec={get_exec_command()}
Icon=awall
Terminal=false
Categories=Utility;DesktopSettings;
X-GNOME-Autostart-enabled=true
StartupNotify=false
"""


def enable_autostart() -> bool:
    """Enables desktop autostart on user login."""
    try:
        f = get_autostart_file()
        f.write_text(generate_desktop_entry(), encoding="utf-8")
        print("[awall] Desktop autostart enabled on user login.")
        return True
    except Exception as e:
        print(f"[awall] Failed to enable autostart: {e}")
        return False


def disable_autostart() -> bool:
    """Disables desktop autostart."""
    try:
        f = get_autostart_file()
        if f.exists():
            f.unlink()
        print("[awall] Desktop autostart disabled.")
        return True
    except Exception as e:
        print(f"[awall] Failed to disable autostart: {e}")
        return False


def is_autostart_enabled() -> bool:
    """Checks if autostart file exists."""
    return get_autostart_file().exists()


def get_autostart_status() -> Dict[str, Any]:
    """Returns autostart status dictionary."""
    f = get_autostart_file()
    return {
        "enabled": f.exists(),
        "file": str(f),
        "command": get_exec_command(),
    }

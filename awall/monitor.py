"""
Monitor and display detection for Linux desktops.
Supports X11, Wayland compositors (Hyprland, Sway, wlroots), and fallback dimension querying.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MonitorInfo:
    name: str
    width: int
    height: int
    is_primary: bool = False


def is_wayland() -> bool:
    """Returns True if the current session is Wayland."""
    return bool(os.environ.get("WAYLAND_DISPLAY")) or os.environ.get("XDG_SESSION_TYPE") == "wayland"


def get_monitors() -> List[MonitorInfo]:
    """
    Detects all active connected monitors and their resolutions.
    """
    monitors: List[MonitorInfo] = []

    # 1. Try Hyprland (hyprctl)
    if shutil.which("hyprctl") and os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        try:
            output = subprocess.check_output(["hyprctl", "monitors", "-j"], timeout=3).decode("utf-8")
            data = json.loads(output)
            for m in data:
                monitors.append(
                    MonitorInfo(
                        name=m.get("name", "Unknown"),
                        width=int(m.get("width", 1920)),
                        height=int(m.get("height", 1080)),
                        is_primary=bool(m.get("focused", False)),
                    )
                )
            if monitors:
                return monitors
        except Exception:
            pass

    # 2. Try Sway (swaymsg)
    if shutil.which("swaymsg") and is_wayland():
        try:
            output = subprocess.check_output(["swaymsg", "-t", "get_outputs"], timeout=3).decode("utf-8")
            data = json.loads(output)
            for m in data:
                if m.get("active"):
                    rect = m.get("rect", {})
                    monitors.append(
                        MonitorInfo(
                            name=m.get("name", "Unknown"),
                            width=int(rect.get("width", 1920)),
                            height=int(rect.get("height", 1080)),
                            is_primary=bool(m.get("focused", False)),
                        )
                    )
            if monitors:
                return monitors
        except Exception:
            pass

    # 3. Try Linux DRM sysfs (/sys/class/drm)
    from pathlib import Path
    drm_dir = Path("/sys/class/drm")
    if drm_dir.exists():
        try:
            for p in sorted(drm_dir.glob("card*-*")):
                st = p / "status"
                if st.exists() and st.read_text().strip() == "connected":
                    raw_name = p.name
                    name = re.sub(r"^card\d+-", "", raw_name)
                    modes_f = p / "modes"
                    w, h = 1920, 1080
                    if modes_f.exists() and modes_f.read_text().strip():
                        top_mode = modes_f.read_text().splitlines()[0].strip()
                        if "x" in top_mode:
                            parts = top_mode.split("x")
                            w, h = int(parts[0]), int(parts[1])
                    monitors.append(
                        MonitorInfo(
                            name=name,
                            width=w,
                            height=h,
                            is_primary=(len(monitors) == 0),
                        )
                    )
            if monitors:
                return monitors
        except Exception:
            pass

    # 4. Try XFCE xfconf-query
    if shutil.which("xfconf-query") and "XFCE" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper():
        try:
            out = subprocess.check_output(
                ["xfconf-query", "-c", "xfce4-desktop", "-l"],
                stderr=subprocess.DEVNULL,
                timeout=3,
            ).decode()
            xfce_mons = []
            for line in out.splitlines():
                m = re.search(r"/backdrop/screen\d+/monitor([^/]+)/", line)
                if m:
                    m_name = m.group(1)
                    if m_name not in xfce_mons and m_name != "0":
                        xfce_mons.append(m_name)
            for idx, m_name in enumerate(xfce_mons):
                monitors.append(
                    MonitorInfo(
                        name=m_name,
                        width=1920,
                        height=1080,
                        is_primary=(idx == 0),
                    )
                )
            if monitors:
                return monitors
        except Exception:
            pass

    # 5. Try xrandr (X11)
    if shutil.which("xrandr"):
        try:
            output = subprocess.check_output(["xrandr", "--query"], timeout=3).decode("utf-8")
            # Example: "HDMI-1 connected primary 1920x1080+0+0"
            pattern = re.compile(r"^(\S+)\s+connected\s+(primary\s+)?(\d+)x(\d+)")
            for line in output.splitlines():
                match = pattern.match(line)
                if match:
                    name = match.group(1)
                    is_prim = bool(match.group(2))
                    w = int(match.group(3))
                    h = int(match.group(4))
                    monitors.append(
                        MonitorInfo(
                            name=name,
                            width=w,
                            height=h,
                            is_primary=is_prim,
                        )
                    )
            if monitors:
                return monitors
        except Exception:
            pass

    # 6. Try Gdk / PyGObject if available
    try:
        import gi
        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk
        display = Gdk.Display.get_default()
        if display:
            mon_list = display.get_monitors()
            for i in range(mon_list.get_n_items()):
                mon = mon_list.get_item(i)
                geometry = mon.get_geometry()
                monitors.append(
                    MonitorInfo(
                        name=f"Monitor-{i}",
                        width=geometry.width,
                        height=geometry.height,
                        is_primary=(i == 0),
                    )
                )
            if monitors:
                return monitors
    except Exception:
        pass

    # 7. Default single monitor fallback
    return [MonitorInfo(name="Default", width=1920, height=1080, is_primary=True)]

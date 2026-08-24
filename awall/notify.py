"""
Desktop notification module for awall.
Uses notify-send / libnotify to display wallpaper changes, photographer credits, and alerts.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional


def is_notify_send_available() -> bool:
    """Check if notify-send command is installed on the system."""
    return shutil.which("notify-send") is not None


def send_notification(
    summary: str,
    body: str = "",
    icon: Optional[str | Path] = None,
    urgency: str = "normal",
    timeout_ms: int = 4000,
) -> bool:
    """
    Sends a desktop notification using notify-send.
    Returns True if notification command was executed.
    """
    if not is_notify_send_available():
        return False

    cmd = [
        "notify-send",
        "--app-name=awall",
        f"--urgency={urgency}",
        f"--expire-time={timeout_ms}",
    ]

    if icon and Path(icon).exists():
        cmd.extend(["--icon", str(Path(icon).resolve())])
    else:
        cmd.extend(["--icon", "preferences-desktop-wallpaper"])

    cmd.append(summary)
    if body:
        cmd.append(body)

    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except Exception as e:
        print(f"[awall] Notification warning: {e}")
        return False


def send_wallpaper_notification(
    photographer: str = "Unknown",
    topic: str = "",
    source: str = "",
    image_path: Optional[str | Path] = None,
    photographer_url: str = "",
    enabled: bool = True,
    show_credits: bool = True,
) -> None:
    """Send a notification when a new wallpaper is applied."""
    if not enabled:
        return

    summary = "🖼 Wallpaper Changed"
    body_parts = []

    if topic:
        clean_topic = topic.replace("_", " ").title()
        body_parts.append(f"Topic: {clean_topic}")

    if show_credits and photographer and photographer != "Unknown":
        body_parts.append(f"Photo by {photographer}")
        if source:
            body_parts.append(f"via {source.title()}")
    elif source:
        body_parts.append(f"Source: {source.title()}")

    body = " • ".join(body_parts)
    send_notification(summary=summary, body=body, icon=image_path, timeout_ms=4500)


def send_offline_notification(image_path: Optional[str | Path] = None) -> None:
    """Send an alert that awall is operating in offline mode with cached wallpapers."""
    summary = "📡 awall: Offline Mode"
    body = "No internet connection. Switched to rotating cached wallpapers."
    send_notification(summary=summary, body=body, icon=image_path, urgency="low")


def send_error_notification(message: str) -> None:
    """Send error notification to user."""
    summary = "⚠️ awall Error"
    send_notification(summary=summary, body=message, urgency="critical")

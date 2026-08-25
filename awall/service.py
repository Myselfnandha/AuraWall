"""
Systemd user service and timer manager for awall on Arch Linux / systemd-based distros.
Handles auto-installation, activation, status querying, and interval synchronization.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def get_systemd_user_dir() -> Path:
    """Returns the user systemd unit directory (~/.config/systemd/user)."""
    path = Path.home() / ".config" / "systemd" / "user"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_awall_executable() -> str:
    """Finds the absolute command to execute awall."""
    which_awall = shutil.which("awall")
    if which_awall:
        return which_awall
    return f"{sys.executable} -m awall"


def generate_service_content() -> str:
    """Generates the systemd user service unit."""
    exec_cmd = f"{get_awall_executable()} next"
    return f"""[Unit]
Description=awall - Free Automatic Wallpaper Engine Service
Documentation=https://github.com/user/awall
After=graphical-session.target network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart={exec_cmd}
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical-session.target
"""


def generate_timer_content(interval_minutes: int = 5, on_boot: bool = True) -> str:
    """Generates the systemd user timer unit."""
    boot_sec = "30s" if on_boot else "2min"
    return f"""[Unit]
Description=awall - Free Automatic Wallpaper Engine Timer
Documentation=https://github.com/user/awall
PartOf=awall.service

[Timer]
OnBootSec={boot_sec}
OnUnitActiveSec={interval_minutes}min
Persistent=true

[Install]
WantedBy=timers.target
"""


class ServiceManager:
    """Controls the installation, lifecycle, and status of awall's systemd timer."""

    def __init__(self):
        self.user_dir = get_systemd_user_dir()
        self.service_file = self.user_dir / "awall.service"
        self.timer_file = self.user_dir / "awall.timer"

    def install(self, interval_minutes: int = 5, on_boot: bool = True) -> bool:
        """Installs and enables the systemd service and timer."""
        try:
            self.service_file.write_text(generate_service_content(), encoding="utf-8")
            self.timer_file.write_text(generate_timer_content(interval_minutes, on_boot), encoding="utf-8")

            # Reload systemd user daemon
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
            subprocess.run(["systemctl", "--user", "enable", "--now", "awall.timer"], check=True)
            print(f"[awall] systemd timer successfully installed and activated (interval: {interval_minutes}m).")
            return True
        except Exception as e:
            print(f"[awall] Failed to install systemd service: {e}")
            return False

    def uninstall(self) -> bool:
        """Stops, disables, and removes the systemd units."""
        try:
            subprocess.run(["systemctl", "--user", "disable", "--now", "awall.timer"], check=False)
            subprocess.run(["systemctl", "--user", "stop", "awall.service"], check=False)

            if self.service_file.exists():
                self.service_file.unlink()
            if self.timer_file.exists():
                self.timer_file.unlink()

            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
            print("[awall] systemd service & timer successfully uninstalled.")
            return True
        except Exception as e:
            print(f"[awall] Failed to uninstall systemd service: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Returns the current status of the service and timer."""
        timer_active = False
        timer_enabled = False
        service_installed = self.service_file.exists() and self.timer_file.exists()

        try:
            res_act = subprocess.run(
                ["systemctl", "--user", "is-active", "awall.timer"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            timer_active = res_act.stdout.strip() == "active"

            res_enb = subprocess.run(
                ["systemctl", "--user", "is-enabled", "awall.timer"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            timer_enabled = res_enb.stdout.strip() == "enabled"
        except Exception:
            pass

        return {
            "installed": service_installed,
            "timer_active": timer_active,
            "timer_enabled": timer_enabled,
            "service_file": str(self.service_file),
            "timer_file": str(self.timer_file),
        }

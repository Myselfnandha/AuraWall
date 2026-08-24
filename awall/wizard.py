"""
Interactive terminal setup wizard for awall.
Guides the user through initial configuration with rich ANSI colors and sensible defaults.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

from awall.config import ALL_TOPICS, get_default_config, load_config, save_config
from awall.service import ServiceManager
from awall.wallpaper_setter import detect_backend

# ANSI Color codes
BOLD = "\033[1m"
GREEN = "\033[92m"
BLUE = "\033[94m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RESET = "\033[0m"


def print_banner():
    banner = f"""
{CYAN}{BOLD}╔═══════════════════════════════════════════════════════════╗
║   {MAGENTA}🖼  awall - Free Automatic Wallpaper Engine Wizard{CYAN}      ║
║   {YELLOW}A modern wallpaper automation tool for Arch Linux{CYAN}       ║
╚═══════════════════════════════════════════════════════════╝{RESET}
"""
    print(banner)


def ask_choice(prompt: str, options: List[str], default_idx: int = 0) -> int:
    """Prompt user to choose one option from a numbered list."""
    print(f"\n{BOLD}{prompt}{RESET}")
    for idx, opt in enumerate(options):
        marker = f"{GREEN}* {RESET}" if idx == default_idx else "  "
        print(f"{marker}[{idx + 1}] {opt}")

    while True:
        try:
            choice = input(f"\n{CYAN}Select option [1-{len(options)}] (default {default_idx + 1}): {RESET}").strip()
            if not choice:
                return default_idx
            num = int(choice) - 1
            if 0 <= num < len(options):
                return num
            print(f"{YELLOW}Please enter a number between 1 and {len(options)}.{RESET}")
        except (ValueError, EOFError):
            return default_idx


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Prompt user for a yes/no question."""
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        ans = input(f"\n{BOLD}{prompt} {CYAN}{suffix}: {RESET}").strip().lower()
        if not ans:
            return default
        return ans in ("y", "yes", "true", "1")
    except EOFError:
        return default


def run_wizard():
    """Runs the full interactive configuration wizard."""
    print_banner()
    config = load_config()

    print(f"{BLUE}Checking desktop environment & wallpaper backend...{RESET}")
    backend = detect_backend()
    if backend:
        print(f"-> Detected desktop backend: {GREEN}{BOLD}{backend.name}{RESET}")
        config["wallpaper_backend"] = "auto"
    else:
        print(f"-> {YELLOW}No specific desktop tool detected. Using auto mode.{RESET}")
        config["wallpaper_backend"] = "auto"

    # Step 1: Sources selection
    print(f"\n{BOLD}{MAGENTA}─── Step 1: Wallpaper Sources ───{RESET}")
    print("Select which sources should be enabled:")
    sources = ["unsplash", "pexels", "pixabay", "reddit", "local"]
    for s in sources:
        enabled = ask_yes_no(f"Enable {s.title()} source?", default=config["sources"].get(s, {}).get("enabled", True))
        config["sources"][s]["enabled"] = enabled

    # Step 2: Topics Selection
    print(f"\n{BOLD}{MAGENTA}─── Step 2: Wallpaper Categories & Topics ───{RESET}")
    topic_mode_idx = ask_choice(
        "Choose how categories should be rotated:",
        [
            "Mixed (Randomly selects from all enabled categories)",
            "Sequential (Cycles through categories one by one)",
        ],
        default=0,
    )
    config["topics"]["mode"] = "mixed" if topic_mode_idx == 0 else "sequential"

    enable_all = ask_yes_no("Enable all 17 default topic categories?", default=True)
    if enable_all:
        config["topics"]["enabled"] = list(ALL_TOPICS)
    else:
        enabled_list = []
        for t in ALL_TOPICS:
            if ask_yes_no(f"Include topic '{t.replace('_', ' ').title()}'?", default=True):
                enabled_list.append(t)
        config["topics"]["enabled"] = enabled_list or ["nature", "wallpapers"]

    # Step 3: Rotation Interval
    print(f"\n{BOLD}{MAGENTA}─── Step 3: Rotation Schedule ───{RESET}")
    interval_options = [
        "Every 5 minutes (Recommended)",
        "Every 15 minutes",
        "Every 30 minutes",
        "Every 1 hour",
        "Every 6 hours",
        "Every day (24 hours)",
        "Every week",
        "Custom minutes",
    ]
    interval_map = [5, 15, 30, 60, 360, 1440, 10080, -1]
    chosen_interval_idx = ask_choice("How often should the wallpaper rotate?", interval_options, default=0)

    if interval_map[chosen_interval_idx] == -1:
        try:
            cust_val = input(f"{CYAN}Enter custom interval in minutes (e.g. 10): {RESET}").strip()
            config["schedule"]["interval_minutes"] = max(1, int(cust_val))
        except (ValueError, EOFError):
            config["schedule"]["interval_minutes"] = 5
    else:
        config["schedule"]["interval_minutes"] = interval_map[chosen_interval_idx]

    # Step 4: Display & Transitions
    print(f"\n{BOLD}{MAGENTA}─── Step 4: Display & Visual Effects ───{RESET}")
    trans_options = [
        "Smooth Fade (Crossfade blend transition)",
        "Instant (Immediate swap)",
        "Slide (Smooth horizontal slide)",
    ]
    trans_map = ["fade", "instant", "slide"]
    trans_idx = ask_choice("Choose transition style:", trans_options, default=0)
    config["display"]["transition"] = trans_map[trans_idx]

    # Step 5: Notifications
    print(f"\n{BOLD}{MAGENTA}─── Step 5: Desktop Notifications ───{RESET}")
    notif_enabled = ask_yes_no("Show desktop notification with photographer credits when wallpaper changes?", default=True)
    config["notifications"]["enabled"] = notif_enabled

    # Step 6: Save Configuration
    save_config(config)
    print(f"\n{GREEN}{BOLD}✓ Configuration successfully saved to ~/.config/auto_wall/config.yaml{RESET}")

    # Step 7: Systemd Service Auto-Install
    print(f"\n{BOLD}{MAGENTA}─── Step 7: Background Automation (systemd) ───{RESET}")
    install_sysd = ask_yes_no("Install and enable systemd user timer to run awall automatically in the background?", default=True)
    if install_sysd:
        svc_mgr = ServiceManager()
        svc_mgr.install(
            interval_minutes=config["schedule"]["interval_minutes"],
            on_boot=config["schedule"].get("on_boot", True),
        )

    # Initial run prompt
    run_now = ask_yes_no("Apply a new wallpaper right now?", default=True)
    if run_now:
        from awall.daemon import change_wallpaper
        print(f"\n{CYAN}Fetching and applying your first wallpaper...{RESET}")
        change_wallpaper(config, ignore_pause=True)

    print(f"\n{GREEN}{BOLD}🎉 All set! Enjoy your dynamic desktop wallpapers with awall!{RESET}\n")

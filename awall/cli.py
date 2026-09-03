"""
Command-line interface (CLI) for awall.
Provides full control over wallpaper rotation, favorites, configuration, and services.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from awall import __version__
from awall.cache import CacheManager
from awall.config import load_config, save_config, update_config
from awall.daemon import change_wallpaper
from awall.history import HistoryManager
from awall.service import ServiceManager
from awall.wallpaper_setter import detect_backend, set_wallpaper

# ANSI styling
BOLD = "\033[1m"
GREEN = "\033[92m"
BLUE = "\033[94m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
DIM = "\033[2m"
RESET = "\033[0m"


def cmd_run(args: argparse.Namespace) -> int:
    """Executes a single wallpaper rotation cycle."""
    config = load_config()
    force_topic = getattr(args, "topic", None)
    force_source = getattr(args, "source", None)
    success = change_wallpaper(config, force_topic=force_topic, force_source=force_source)
    return 0 if success else 1


def cmd_next(args: argparse.Namespace) -> int:
    """Fetches and sets the next wallpaper."""
    config = load_config()
    force_topic = getattr(args, "topic", None)
    force_source = getattr(args, "source", None)
    force = getattr(args, "force", False)
    is_scheduled = getattr(args, "scheduled", False) or bool(os.environ.get("INVOCATION_ID"))

    # 1. Master Pause Check
    if config.get("paused", False) and not force:
        print(f"{YELLOW}⏸ Wallpaper rotation is currently PAUSED. (Use 'awall next -f' to force or 'awall resume' to resume){RESET}")
        return 0

    # 2. If scheduled background invocation, respect Smart Window Pause & Running Tray Watcher
    if (is_scheduled or not sys.stdin.isatty()) and not force:
        pause_on_window = config.get("schedule", {}).get("pause_on_active_window", True)
        if pause_on_window:
            from awall.window_watcher import check_active_window_state
            is_desktop, is_fullscreen = check_active_window_state()
            if not is_desktop or is_fullscreen:
                reason = "fullscreen application active" if is_fullscreen else "application window active"
                print(f"[awall] Wallpaper rotation paused ({reason}). Skipping scheduled rotation.")
                return 0

        # If tray daemon is already actively running, let its event-driven SmartRotationWatcher handle rotation
        from awall.gui.app import is_tray_running
        if is_tray_running():
            return 0

    success = change_wallpaper(
        config=config,
        force_topic=force_topic,
        force_source=force_source,
        ignore_pause=force,
    )
    return 0 if success else 1


def cmd_prev(args: argparse.Namespace) -> int:
    """Reverts to the previous wallpaper in history."""
    history_mgr = HistoryManager()
    history = history_mgr.get_history(limit=5)
    if len(history) < 2:
        print(f"{YELLOW}No previous wallpaper found in history.{RESET}")
        return 1

    prev_entry = history[1]  # history[0] is current
    file_path = prev_entry.get("file_path")
    if not file_path or not Path(file_path).exists():
        print(f"{RED}Previous wallpaper file no longer exists on disk.{RESET}")
        return 1

    config = load_config()
    backend_override = config.get("wallpaper_backend", "auto")
    scaling = config.get("display", {}).get("scaling", "fill")

    success = set_wallpaper(
        file_path,
        scaling=scaling,
        backend_override=backend_override,
    )
    if success:
        print(f"{GREEN}✓ Restored previous wallpaper:{RESET} {Path(file_path).name}")
        print(f"  Photographer: {BOLD}{prev_entry.get('photographer')}{RESET}")
        print(f"  Source: {prev_entry.get('source')} | Topic: {prev_entry.get('topic')}")
        return 0
    return 1


def cmd_fav(args: argparse.Namespace) -> int:
    """Marks the current (or specified) wallpaper as a favorite."""
    history_mgr = HistoryManager()
    target = getattr(args, "id_or_path", None)
    entry = history_mgr.mark_favorite(file_path_or_id=target, is_fav=True)
    if entry:
        print(f"{GREEN}{BOLD}★ Added to Favorites:{RESET} {Path(entry.get('file_path', '')).name}")
        print(f"  Photographer: {BOLD}{entry.get('photographer')}{RESET}")
        print(f"  Saved wallpapers will never be auto-deleted by cache cleaner.")
        return 0
    print(f"{RED}Could not find active or specified wallpaper.{RESET}")
    return 1


def cmd_unfav(args: argparse.Namespace) -> int:
    """Removes the favorite tag from the wallpaper."""
    history_mgr = HistoryManager()
    target = getattr(args, "id_or_path", None)
    entry = history_mgr.mark_favorite(file_path_or_id=target, is_fav=False)
    if entry:
        print(f"{YELLOW}Removed from Favorites:{RESET} {Path(entry.get('file_path', '')).name}")
        return 0
    print(f"{RED}Could not find active or specified wallpaper.{RESET}")
    return 1


def cmd_favorites(args: argparse.Namespace) -> int:
    """Lists all favorited wallpapers."""
    history_mgr = HistoryManager()
    favs = history_mgr.get_favorites()
    if not favs:
        print(f"{YELLOW}No favorite wallpapers yet. Use 'awall fav' to mark the current wallpaper!{RESET}")
        return 0

    print(f"\n{BOLD}{MAGENTA}★ Your Favorite Wallpapers ({len(favs)}){RESET}\n")
    for f in favs:
        print(f" {GREEN}★{RESET} {BOLD}{f.get('id')}{RESET}  {Path(f.get('file_path', '')).name}")
        print(f"    Author: {f.get('photographer')} | Source: {f.get('source')} | Topic: {f.get('topic')}")
        if f.get("url"):
            print(f"    {DIM}URL: {f.get('url')}{RESET}")
    print()
    return 0


def cmd_set_source(args: argparse.Namespace) -> int:
    """Quickly switch active wallpaper source."""
    valid_sources = ["auto", "unsplash", "pexels", "pixabay", "reddit", "local"]
    source = args.source.lower()
    if source not in valid_sources:
        print(f"{RED}Invalid source '{source}'. Choose from: {', '.join(valid_sources)}{RESET}")
        return 1

    config = load_config()
    config["active_source"] = source
    save_config(config)
    print(f"{GREEN}✓ Active wallpaper source set to:{RESET} {BOLD}{source}{RESET}")
    return 0


def cmd_pause(args: argparse.Namespace) -> int:
    """Pauses automatic wallpaper rotation."""
    config = load_config()
    config["paused"] = True
    save_config(config)
    print(f"{YELLOW}⏸ Wallpaper rotation PAUSED.{RESET}")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    """Resumes automatic wallpaper rotation."""
    config = load_config()
    config["paused"] = False
    save_config(config)
    print(f"{GREEN}▶ Wallpaper rotation RESUMED.{RESET}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Displays engine and systemd timer status."""
    config = load_config()
    history_mgr = HistoryManager()
    cache_mgr = CacheManager(cache_dir=config.get("cache", {}).get("directory"))
    svc_mgr = ServiceManager()

    curr = history_mgr.get_current()
    files_count, total_mb = cache_mgr.get_stats()
    svc_status = svc_mgr.get_status()
    backend = detect_backend(config.get("wallpaper_backend"))

    print(f"\n{BOLD}{CYAN}─── awall Status ───{RESET}")
    paused = config.get("paused", False)
    state_str = f"{YELLOW}PAUSED ⏸{RESET}" if paused else f"{GREEN}ACTIVE ▶{RESET}"
    print(f"  State:             {state_str}")
    print(f"  Active Source:     {BOLD}{config.get('active_source', 'auto')}{RESET}")
    print(f"  Rotation Interval: {config.get('schedule', {}).get('interval_minutes', 5)} minutes")
    print(f"  Desktop Backend:   {GREEN}{backend.name if backend else 'None'}{RESET}")
    print(f"  Cache Files:       {files_count} ({total_mb:.1f} MB)")

    sysd_str = f"{GREEN}Running (active){RESET}" if svc_status.get("timer_active") else f"{RED}Inactive{RESET}"
    print(f"  systemd Timer:     {sysd_str}")

    if curr:
        fav_mark = f"{GREEN}★ (Favorite){RESET}" if curr.get("is_favorite") else ""
        print(f"\n{BOLD}{MAGENTA}─── Current Wallpaper ───{RESET}")
        print(f"  File:              {Path(curr.get('file_path', '')).name} {fav_mark}")
        print(f"  Photographer:      {BOLD}{curr.get('photographer')}{RESET}")
        print(f"  Source / Topic:    {curr.get('source')} / {curr.get('topic')}")
        if curr.get("photographer_url"):
            print(f"  Credit Link:       {CYAN}{curr.get('photographer_url')}{RESET}")
    print()
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Shows detailed information about the current wallpaper."""
    history_mgr = HistoryManager()
    curr = history_mgr.get_current()
    if not curr:
        print(f"{YELLOW}No wallpaper has been set yet with awall.{RESET}")
        return 1

    print(f"\n{BOLD}{CYAN}🖼 Wallpaper Information{RESET}")
    print(f"  File:              {curr.get('file_path')}")
    print(f"  Photographer:      {BOLD}{curr.get('photographer')}{RESET}")
    print(f"  Photographer Link: {curr.get('photographer_url') or 'N/A'}")
    print(f"  Source:            {curr.get('source')}")
    print(f"  Topic/Category:    {curr.get('topic')}")
    print(f"  Original URL:      {curr.get('url') or 'N/A'}")
    print(f"  Applied At:        {curr.get('timestamp')}")
    print(f"  Favorite:          {'Yes ★' if curr.get('is_favorite') else 'No'}")
    print()
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    """Shows the recent history of wallpapers."""
    limit = getattr(args, "limit", 15) or 15
    history_mgr = HistoryManager()
    entries = history_mgr.get_history(limit=limit)
    if not entries:
        print(f"{YELLOW}No wallpaper history found.{RESET}")
        return 0

    print(f"\n{BOLD}{MAGENTA}Recent Wallpaper History (last {len(entries)}){RESET}\n")
    for idx, e in enumerate(entries):
        fav = f"{GREEN}★{RESET}" if e.get("is_favorite") else " "
        print(f" [{idx + 1:02d}] {fav} {BOLD}{Path(e.get('file_path', '')).name}{RESET}")
        print(f"      by {e.get('photographer')} ({e.get('source')} - {e.get('topic')}) | {e.get('timestamp')[:19]}")
    print()
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Launches GTK4 GUI settings window."""
    from awall.gui.app import launch_gui
    return launch_gui()


def cmd_tray(args: argparse.Namespace) -> int:
    """Launches the system tray icon."""
    from awall.tray import run_tray
    return run_tray()


def cmd_autostart(args: argparse.Namespace) -> int:
    """Manages XDG desktop login autostart for tray."""
    from awall.autostart import disable_autostart, enable_autostart, get_autostart_status
    action = getattr(args, "action", "status")
    if action == "enable":
        return 0 if enable_autostart() else 1
    elif action == "disable":
        return 0 if disable_autostart() else 1
    else:
        st = get_autostart_status()
        print(f"\n{BOLD}Desktop Autostart Status:{RESET}")
        print(f"  Autostart Enabled: {'Yes ✓' if st['enabled'] else 'No ✗'}")
        print(f"  Entry File:        {st['file']}")
        print(f"  Command:           {st['command']}\n")
        return 0


def cmd_app(args: argparse.Namespace) -> int:
    """Manages desktop application launcher (.desktop) and icons."""
    from awall.desktop import (
        get_desktop_app_status,
        install_desktop_app,
        uninstall_desktop_app,
    )
    action = getattr(args, "action", "status")
    if action == "install":
        return 0 if install_desktop_app() else 1
    elif action == "uninstall":
        return 0 if uninstall_desktop_app() else 1
    else:
        st = get_desktop_app_status()
        print(f"\n{BOLD}Desktop Application Status:{RESET}")
        print(f"  Application Installed: {'Yes ✓' if st['installed'] else 'No ✗'}")
        print(f"  Launcher File:         {st['file']}")
        print(f"  Command:               {st['command']}\n")
        return 0


def cmd_weather(args: argparse.Namespace) -> int:
    """Displays current solar position and live weather conditions."""
    from awall.weather import calculate_solar_phase, get_live_weather, get_location
    config = load_config()
    lat, lon, city = get_location(config)
    solar_phase, elevation = calculate_solar_phase(lat, lon)
    weather_info = get_live_weather(lat, lon)

    print(f"\n{BOLD}{CYAN}☀️ Solar Position & Live Weather{RESET}")
    print(f"  Location:          {BOLD}{city}{RESET} ({lat:.2f}°, {lon:.2f}°)")
    print(f"  Solar Phase:       {BOLD}{solar_phase.replace('_', ' ').title()}{RESET} (Elevation: {elevation:.1f}°)")
    print(f"  Temperature:       {weather_info.get('icon', '☀️')} {weather_info.get('temperature')}°C")
    print(f"  Condition:         {weather_info.get('description')} (Mood: {weather_info.get('mood')})")
    print(f"  Daylight:          {'Daytime ☀️' if weather_info.get('is_day') else 'Nighttime 🌙'}\n")
    return 0


def cmd_service(args: argparse.Namespace) -> int:
    """Manages systemd user service and timer."""
    action = args.action.lower()
    svc_mgr = ServiceManager()
    config = load_config()

    if action == "install":
        interval = config.get("schedule", {}).get("interval_minutes", 5)
        on_boot = config.get("schedule", {}).get("on_boot", True)
        success = svc_mgr.install(interval_minutes=interval, on_boot=on_boot)
        return 0 if success else 1
    elif action == "uninstall":
        success = svc_mgr.uninstall()
        return 0 if success else 1
    elif action == "status":
        st = svc_mgr.get_status()
        print(f"\n{BOLD}systemd User Service Status:{RESET}")
        print(f"  Units Installed: {st.get('installed')}")
        print(f"  Timer Active:    {st.get('timer_active')}")
        print(f"  Timer Enabled:   {st.get('timer_enabled')}")
        print(f"  Service Unit:    {st.get('service_file')}")
        print(f"  Timer Unit:      {st.get('timer_file')}\n")
        return 0
    else:
        print(f"{RED}Unknown service action '{action}'. Choose from: install, uninstall, status{RESET}")
        return 1


def main(argv: Optional[list[str]] = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="awall",
        description="Free Automatic Wallpaper Engine for Arch Linux & beyond.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # run
    p_run = subparsers.add_parser("run", help="Run a single rotation cycle (used by systemd)")
    p_run.add_argument("--topic", help="Override topic for this run")
    p_run.add_argument("--source", help="Override source for this run")
    p_run.set_defaults(func=cmd_run)

    # next
    p_next = subparsers.add_parser("next", help="Skip immediately to next wallpaper")
    p_next.add_argument("--topic", help="Specific topic")
    p_next.add_argument("--source", help="Specific source")
    p_next.set_defaults(func=cmd_next)

    # prev
    p_prev = subparsers.add_parser("prev", help="Revert to previous wallpaper in history")
    p_prev.set_defaults(func=cmd_prev)

    # fav
    p_fav = subparsers.add_parser("fav", help="Mark current wallpaper as favorite")
    p_fav.add_argument("id_or_path", nargs="?", default=None, help="Wallpaper ID or file path")
    p_fav.set_defaults(func=cmd_fav)

    # unfav
    p_unfav = subparsers.add_parser("unfav", help="Remove favorite mark from wallpaper")
    p_unfav.add_argument("id_or_path", nargs="?", default=None, help="Wallpaper ID or file path")
    p_unfav.set_defaults(func=cmd_unfav)

    # favorites
    p_favs = subparsers.add_parser("favorites", aliases=["favs"], help="List all favorite wallpapers")
    p_favs.set_defaults(func=cmd_favorites)

    # set-source
    p_src = subparsers.add_parser("set-source", help="Set active source (unsplash, pexels, pixabay, reddit, local, auto)")
    p_src.add_argument("source", help="Source identifier")
    p_src.set_defaults(func=cmd_set_source)

def cmd_lockscreen(args) -> int:
    from awall.config import load_config
    from awall.history import HistoryManager
    from awall.lockscreen import detect_lock_screen_backend, sync_lock_screen

    config = load_config()
    backend = detect_lock_screen_backend()

    if args.action == "status":
        lock_cfg = config.get("display", {}).get("lock_screen", {})
        enabled = lock_cfg.get("enabled", True)
        effect = lock_cfg.get("effect", "none")
        print("🔒 Lock Screen Sync Status:")
        print(f"  • Enabled:          {'Yes' if enabled else 'No'}")
        print(f"  • Detected Backend: {backend}")
        print(f"  • Visual Effect:    {effect}")
        print(f"  • Blur Radius:      {lock_cfg.get('blur_radius', 15)}")
        print(f"  • Dim Opacity:      {lock_cfg.get('dim_opacity', 0.4)}")
        return 0

    if args.action == "sync":
        hist = HistoryManager()
        curr = hist.get_current()
        path = Path(curr["file_path"]) if curr and curr.get("file_path") else None
        if not path or not path.exists():
            from awall.cache import CacheManager
            cache_mgr = CacheManager()
            path = cache_mgr.get_offline_wallpaper()

        if not path or not path.exists():
            print("[awall] Error: No valid wallpaper found in cache or history to sync.")
            return 1

        print(f"[awall] Syncing wallpaper ({path.name}) to lock screen ({backend})...")
        ok = sync_lock_screen(path, config=config)
        if ok:
            print("[awall] ✓ Lock screen wallpaper successfully updated!")
            return 0
        else:
            print("[awall] ✗ Failed to sync lock screen wallpaper.")
            return 1
    return 0


def cmd_monitors(args) -> int:
    from awall.config import load_config
    from awall.monitor import get_monitors

    config = load_config()
    disp_cfg = config.get("display", {})
    multi_mode = disp_cfg.get("multi_monitor", "unified")
    mon_cfgs = disp_cfg.get("monitor_config", {})

    monitors = get_monitors()
    print(f"🖥 Connected Displays ({len(monitors)}):")
    print(f"  • Multi-Monitor Mode: {multi_mode.upper()}")
    for m in monitors:
        mode = mon_cfgs.get(m.name, {}).get("mode", "unique")
        prim_str = " (★ Primary)" if m.is_primary else ""
        print(f"  • {m.name}: {m.width}x{m.height}{prim_str} -> Mode: {mode}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="awall",
        description="🖼 awall — Modern Automatic Wallpaper Engine for Linux",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # next & prev
    p_next = subparsers.add_parser("next", aliases=["run", "rotate", "cycle"], help="Rotate to next wallpaper")
    p_next.add_argument("-t", "--topic", help="Specific topic to fetch")
    p_next.add_argument("-s", "--source", choices=["wallhaven", "bing", "unsplash", "pexels", "pixabay", "reddit", "local"], help="Force specific source")
    p_next.add_argument("-f", "--force", action="store_true", help="Force rotation even if rotation is paused")
    p_next.add_argument("--scheduled", action="store_true", help="Invoked by automatic background scheduler")
    p_next.set_defaults(func=cmd_next)

    p_prev = subparsers.add_parser("prev", help="Revert to previous wallpaper in history")
    p_prev.set_defaults(func=cmd_prev)

    # favorites
    p_fav = subparsers.add_parser("fav", aliases=["favorite"], help="Favorite current wallpaper")
    p_fav.set_defaults(func=cmd_fav)

    p_unfav = subparsers.add_parser("unfav", aliases=["unfavorite"], help="Unfavorite current wallpaper")
    p_unfav.set_defaults(func=cmd_unfav)

    p_favs = subparsers.add_parser("favorites", help="List all favorited wallpapers")
    p_favs.set_defaults(func=cmd_favorites)

    # pause & resume
    p_pause = subparsers.add_parser("pause", help="Pause automatic rotation")
    p_pause.set_defaults(func=cmd_pause)

    p_resume = subparsers.add_parser("resume", help="Resume automatic rotation")
    p_resume.set_defaults(func=cmd_resume)

    # status & info
    p_status = subparsers.add_parser("status", help="Show current state and systemd status")
    p_status.set_defaults(func=cmd_status)

    p_info = subparsers.add_parser("info", help="Show photographer credits & URL for current wallpaper")
    p_info.set_defaults(func=cmd_info)

    # history
    p_hist = subparsers.add_parser("history", help="Show recent wallpaper history")
    p_hist.add_argument("-n", "--limit", type=int, default=15, help="Number of records to show")
    p_hist.set_defaults(func=cmd_history)

    # config / settings
    p_cfg = subparsers.add_parser("config", aliases=["settings"], help="Launch GTK4 settings GUI window")
    p_cfg.set_defaults(func=cmd_config)

    # gui shortcut
    p_gui = subparsers.add_parser("gui", help="Launch GTK4 settings GUI window")
    p_gui.set_defaults(func=cmd_config)

    # tray
    p_tray = subparsers.add_parser("tray", help="Launch desktop system tray icon with quick actions")
    p_tray.set_defaults(func=cmd_tray)

    # autostart
    p_auto = subparsers.add_parser("autostart", help="Manage desktop login autostart for tray")
    p_auto.add_argument("action", nargs="?", default="status", choices=["enable", "disable", "status"], help="Autostart action")
    p_auto.set_defaults(func=cmd_autostart)

    # app menu integration
    p_app = subparsers.add_parser("app", help="Manage desktop application menu entry (.desktop) & icons")
    p_app.add_argument("action", nargs="?", default="status", choices=["install", "uninstall", "status"], help="Desktop app action")
    p_app.set_defaults(func=cmd_app)

    # weather
    p_wtr = subparsers.add_parser("weather", help="Show current solar position, elevation, and live weather")
    p_wtr.set_defaults(func=cmd_weather)

    # service
    p_svc = subparsers.add_parser("service", help="Manage systemd user service & timer")
    p_svc.add_argument("action", choices=["install", "uninstall", "status"], help="Action to perform")
    p_svc.set_defaults(func=cmd_service)

    # lockscreen
    p_lock = subparsers.add_parser("lockscreen", help="Manage lock screen wallpaper synchronization")
    p_lock.add_argument("action", nargs="?", default="status", choices=["sync", "status"], help="Lock screen action")
    p_lock.set_defaults(func=cmd_lockscreen)

    # monitors
    p_mon = subparsers.add_parser("monitors", help="List connected display monitors and multi-monitor setup")
    p_mon.set_defaults(func=cmd_monitors)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        # Default behavior: launch GUI settings desktop application directly
        from awall.gui.app import launch_gui
        return launch_gui()

    res = args.func(args)
    return res if isinstance(res, int) else 0


if __name__ == "__main__":
    sys.exit(main())

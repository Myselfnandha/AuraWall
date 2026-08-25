"""
System tray icon and menu for awall.
Uses AppIndicator3 / Gtk to provide a desktop tray indicator with quick actions.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

from awall.config import ALL_TOPICS, load_config, save_config
from awall.daemon import change_wallpaper
from awall.history import HistoryManager
from awall.wallpaper_setter import set_wallpaper
from awall.window_watcher import SmartRotationManager


def is_tray_available() -> bool:
    """Check if GTK and AppIndicator or StatusIcon are available."""
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        try:
            gi.require_version("AppIndicator3", "0.1")
            from gi.repository import AppIndicator3
        except Exception:
            try:
                gi.require_version("AyatanaAppIndicator3", "0.1")
                from gi.repository import AyatanaAppIndicator3
            except Exception:
                pass
        from gi.repository import Gtk
        return True
    except Exception:
        return False


def run_tray():
    """Runs the system tray icon process."""
    if not is_tray_available():
        print("[awall] System tray requires 'python-gobject', 'gtk3', and 'libappindicator-gtk3'.")
        print("Please install them with: sudo pacman -S libappindicator-gtk3")
        return 1

    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk

    AppInd = None
    try:
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import AppIndicator3 as AppInd
    except Exception:
        try:
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import AyatanaAppIndicator3 as AppInd
        except Exception:
            pass

    def _get_icon_path() -> Optional[str]:
        assets_dir = Path(__file__).parent / "assets"
        for name in ("tray-icon.png", "icon-32.png", "icon.png"):
            p = assets_dir / name
            if p.exists():
                return str(p.resolve())
        return None

    class AwallTrayIcon:
        def __init__(self):
            self.history_mgr = HistoryManager()
            self.config = load_config()
            self.indicator = None
            self.status_icon = None

            assets_dir = (Path(__file__).parent / "assets").resolve()
            icon_name = "tray-icon" if (assets_dir / "tray-icon.png").exists() else "awall"

            if AppInd:
                self.indicator = AppInd.Indicator.new(
                    "awall-tray",
                    icon_name,
                    AppInd.IndicatorCategory.APPLICATION_STATUS,
                )
                if assets_dir.exists():
                    self.indicator.set_icon_theme_path(str(assets_dir))
                self.indicator.set_icon_full(icon_name, "awall Wallpaper Engine")
                self.indicator.set_title("awall Wallpaper Engine")
                self.indicator.set_status(AppInd.IndicatorStatus.ACTIVE)
            else:
                self.status_icon = Gtk.StatusIcon()
                tray_file = assets_dir / "tray-icon.png"
                if tray_file.exists():
                    self.status_icon.set_from_file(str(tray_file))
                else:
                    self.status_icon.set_from_icon_name("preferences-desktop-wallpaper")
                self.status_icon.set_tooltip_text("awall - Wallpaper Engine")
                self.status_icon.set_visible(True)

            self.menu = Gtk.Menu()
            self.build_menu()

            if self.indicator:
                self.indicator.set_menu(self.menu)
            elif self.status_icon:
                self.status_icon.connect("popup-menu", self._on_status_icon_popup)
                self.status_icon.connect("activate", self._on_status_icon_activate)

            # System-triggered smart active-window watcher & power-saving auto-rotator
            self.rotation_mgr = SmartRotationManager(on_trigger_callback=self._async_auto_rotate)
            self.rotation_mgr.start()

        def _on_status_icon_popup(self, icon, button, time):
            self.build_menu()
            self.menu.show_all()
            self.menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, button, time)

        def _on_status_icon_activate(self, icon):
            self.build_menu()
            self.menu.show_all()
            self.menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, 0, Gtk.get_current_event_time())

        def _async_auto_rotate(self):
            threading.Thread(target=self._auto_rotate_worker, daemon=True).start()

        def _auto_rotate_worker(self):
            change_wallpaper(ignore_pause=False)
            GLib.idle_add(self.build_menu)

        def build_menu(self):
            # Clear existing items
            for child in self.menu.get_children():
                self.menu.remove(child)

            self.config = load_config()
            curr = self.history_mgr.get_current()

            # 1. Header Info item
            if curr:
                title_text = f"🖼 {curr.get('photographer', 'Unknown')} ({curr.get('topic', 'wall')})"
                header_item = Gtk.MenuItem(label=title_text)
                header_item.set_sensitive(False)
                self.menu.append(header_item)

                is_fav = curr.get("is_favorite", False)
                fav_label = "★ Unfavorite Wallpaper" if is_fav else "☆ Favorite Current Wallpaper"
                fav_item = Gtk.MenuItem(label=fav_label)
                fav_item.connect("activate", self._toggle_favorite)
                self.menu.append(fav_item)

                self.menu.append(Gtk.SeparatorMenuItem())

            # 2. Next Wallpaper
            next_item = Gtk.MenuItem(label="⏭ Next Wallpaper")
            next_item.connect("activate", self._on_next)
            self.menu.append(next_item)

            # 3. Previous Wallpaper
            prev_item = Gtk.MenuItem(label="⏮ Previous Wallpaper")
            prev_item.connect("activate", self._on_prev)
            self.menu.append(prev_item)

            # 4. Pause / Resume
            paused = self.config.get("paused", False)
            pause_label = "▶ Resume Rotation" if paused else "⏸ Pause Rotation"
            pause_item = Gtk.MenuItem(label=pause_label)
            pause_item.connect("activate", self._toggle_pause)
            self.menu.append(pause_item)

            self.menu.append(Gtk.SeparatorMenuItem())

            # 5. Quick Source Selection Submenu
            source_menu = Gtk.Menu()
            source_item = Gtk.MenuItem(label="🌐 Active Source")
            source_item.set_submenu(source_menu)

            sources_list = [
                ("Automatic (Fallback Chain)", "auto"),
                ("Unsplash", "unsplash"),
                ("Pexels", "pexels"),
                ("Pixabay", "pixabay"),
                ("Reddit", "reddit"),
                ("Local Folder", "local"),
            ]
            active_src = self.config.get("active_source", "auto")
            for label, src_id in sources_list:
                chk = "● " if src_id == active_src else "○ "
                sub_item = Gtk.MenuItem(label=f"{chk}{label}")
                sub_item.connect("activate", self._set_source, src_id)
                source_menu.append(sub_item)
            self.menu.append(source_item)

            # 6. Quick Category Selection Submenu
            topic_menu = Gtk.Menu()
            topic_item = Gtk.MenuItem(label="🏷 Rotate Specific Category")
            topic_item.set_submenu(topic_menu)

            for t in ALL_TOPICS:
                clean_t = t.replace("_", " ").title()
                sub_topic_item = Gtk.MenuItem(label=clean_t)
                sub_topic_item.connect("activate", self._change_specific_topic, t)
                topic_menu.append(sub_topic_item)
            self.menu.append(topic_item)

            self.menu.append(Gtk.SeparatorMenuItem())

            # 7. Open GUI Settings
            settings_item = Gtk.MenuItem(label="⚙ Settings Panel...")
            settings_item.connect("activate", self._open_settings)
            self.menu.append(settings_item)

            # 8. Quit Tray
            quit_item = Gtk.MenuItem(label="🚪 Quit Tray Icon")
            quit_item.connect("activate", self._on_quit)
            self.menu.append(quit_item)

            self.menu.show_all()

        def _on_quit(self, _):
            self.rotation_mgr.stop()
            Gtk.main_quit()

        def _on_next(self, _):
            threading.Thread(target=self._async_next, daemon=True).start()

        def _async_next(self):
            change_wallpaper(ignore_pause=True)
            self.rotation_mgr.record_change()
            GLib.idle_add(self.build_menu)

        def _on_prev(self, _):
            history = self.history_mgr.get_history(limit=5)
            if len(history) >= 2:
                prev_entry = history[1]
                p = prev_entry.get("file_path")
                if p and Path(p).exists():
                    set_wallpaper(p, scaling=self.config.get("display", {}).get("scaling", "fill"))
                    self.rotation_mgr.record_change()
            GLib.idle_add(self.build_menu)

        def _toggle_favorite(self, _):
            curr = self.history_mgr.get_current()
            if curr:
                new_state = not curr.get("is_favorite", False)
                self.history_mgr.mark_favorite(file_path_or_id=curr.get("id"), is_fav=new_state)
            self.build_menu()

        def _toggle_pause(self, _):
            self.config = load_config()
            self.config["paused"] = not self.config.get("paused", False)
            save_config(self.config)
            self.build_menu()

        def _set_source(self, _, source_id: str):
            self.config = load_config()
            self.config["active_source"] = source_id
            save_config(self.config)
            self.build_menu()

        def _change_specific_topic(self, _, topic_id: str):
            def _worker():
                change_wallpaper(force_topic=topic_id, ignore_pause=True)
                self.rotation_mgr.record_change()
                GLib.idle_add(self.build_menu)

            threading.Thread(target=_worker, daemon=True).start()

        def _open_settings(self, _):
            subprocess.Popen([sys.executable, "-m", "awall", "gui"])

    AwallTrayIcon()
    Gtk.main()
    return 0

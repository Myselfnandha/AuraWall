"""
General settings panel (schedule, display, transitions, cache, notifications) for GTK4/Libadwaita GUI.
"""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk
from typing import Any, Dict

from awall.autostart import disable_autostart, enable_autostart, is_autostart_enabled
from awall.desktop import install_desktop_app, is_desktop_app_installed, uninstall_desktop_app
from awall.service import ServiceManager


class GeneralSettingsPage(Adw.PreferencesPage):
    """Settings page for schedule intervals, display effects, cache, and notifications."""

    def __init__(self, config: Dict[str, Any], on_change_callback):
        super().__init__()
        self.set_title("Preferences")
        self.set_icon_name("preferences-system-symbolic")
        self.config = config
        self.on_change = on_change_callback
        self.svc_mgr = ServiceManager()

        self._build_ui()

    def _build_ui(self):
        # 1. Schedule Group
        sched_cfg = self.config.setdefault("schedule", {})
        sched_group = Adw.PreferencesGroup()
        sched_group.set_title("Rotation Schedule")
        self.add(sched_group)

        interval_row = Adw.ComboRow()
        interval_row.set_title("Rotation Interval")
        model = Gtk.StringList()
        intervals_map = [
            ("Every 5 minutes", 5),
            ("Every 15 minutes", 15),
            ("Every 30 minutes", 30),
            ("Every 1 hour", 60),
            ("Every 6 hours", 360),
            ("Every 24 hours (Daily)", 1440),
            ("Every week", 10080),
        ]
        curr_int = sched_cfg.get("interval_minutes", 5)
        selected_idx = 0
        for idx, (label, val) in enumerate(intervals_map):
            model.append(label)
            if val == curr_int:
                selected_idx = idx

        interval_row.set_model(model)
        interval_row.set_selected(selected_idx)

        def _on_interval_change(row, gparam):
            sel = row.get_selected()
            if 0 <= sel < len(intervals_map):
                sched_cfg["interval_minutes"] = intervals_map[sel][1]
                self.on_change()
                # Update running systemd timer if installed
                status = self.svc_mgr.get_status()
                if status.get("installed"):
                    self.svc_mgr.install(
                        interval_minutes=sched_cfg["interval_minutes"],
                        on_boot=sched_cfg.get("on_boot", True),
                    )

        interval_row.connect("notify::selected", _on_interval_change)
        sched_group.add(interval_row)

        boot_row = Adw.SwitchRow()
        boot_row.set_title("Rotate on System Boot")
        boot_row.set_active(sched_cfg.get("on_boot", True))

        def _on_boot_change(row, gparam):
            sched_cfg["on_boot"] = row.get_active()
            self.on_change()

        boot_row.connect("notify::active", _on_boot_change)
        sched_group.add(boot_row)

        # 2. Display & Transitions Group
        disp_cfg = self.config.setdefault("display", {})
        disp_group = Adw.PreferencesGroup()
        disp_group.set_title("Display & Visual Effects")
        self.add(disp_group)

        scaling_row = Adw.ComboRow()
        scaling_row.set_title("Wallpaper Scaling")
        scaling_model = Gtk.StringList()
        scalings = ["fill", "fit", "stretch", "center", "tile"]
        for s in scalings:
            scaling_model.append(s.title())
        scaling_row.set_model(scaling_model)
        curr_scale = disp_cfg.get("scaling", "fill")
        scaling_row.set_selected(scalings.index(curr_scale) if curr_scale in scalings else 0)

        def _on_scale_change(row, gparam):
            sel = row.get_selected()
            if 0 <= sel < len(scalings):
                disp_cfg["scaling"] = scalings[sel]
                self.on_change()

        scaling_row.connect("notify::selected", _on_scale_change)
        disp_group.add(scaling_row)

        trans_row = Adw.ComboRow()
        trans_row.set_title("Transition Animation")
        trans_model = Gtk.StringList()
        transitions = ["fade", "instant", "slide"]
        for t in transitions:
            trans_model.append(t.title())
        trans_row.set_model(trans_model)
        curr_trans = disp_cfg.get("transition", "fade")
        trans_row.set_selected(transitions.index(curr_trans) if curr_trans in transitions else 0)

        def _on_trans_change(row, gparam):
            sel = row.get_selected()
            if 0 <= sel < len(transitions):
                disp_cfg["transition"] = transitions[sel]
                self.on_change()

        trans_row.connect("notify::selected", _on_trans_change)
        disp_group.add(trans_row)

        # 3. Cache Group
        cache_cfg = self.config.setdefault("cache", {})
        cache_group = Adw.PreferencesGroup()
        cache_group.set_title("Cache Storage")
        self.add(cache_group)

        cache_spin_row = Adw.SpinRow.new_with_range(10, 500, 10)
        cache_spin_row.set_title("Maximum Cached Wallpapers")
        cache_spin_row.set_value(float(cache_cfg.get("max_wallpapers", 50)))

        def _on_cache_limit_change(row, gparam):
            cache_cfg["max_wallpapers"] = int(row.get_value())
            self.on_change()

        cache_spin_row.connect("notify::value", _on_cache_limit_change)
        cache_group.add(cache_spin_row)

        # 4. Notifications Group
        notif_cfg = self.config.setdefault("notifications", {})
        notif_group = Adw.PreferencesGroup()
        notif_group.set_title("Notifications")
        self.add(notif_group)

        notif_row = Adw.SwitchRow()
        notif_row.set_title("Desktop Notifications")
        notif_row.set_subtitle("Show alert when wallpaper changes")
        notif_row.set_active(notif_cfg.get("enabled", True))

        def _on_notif_change(row, gparam):
            notif_cfg["enabled"] = row.get_active()
            self.on_change()

        notif_row.connect("notify::active", _on_notif_change)
        notif_group.add(notif_row)

        credit_row = Adw.SwitchRow()
        credit_row.set_title("Show Photographer Credits")
        credit_row.set_active(notif_cfg.get("show_credits", True))

        def _on_credit_change(row, gparam):
            notif_cfg["show_credits"] = row.get_active()
            self.on_change()

        credit_row.connect("notify::active", _on_credit_change)
        notif_group.add(credit_row)

        # 5. Desktop & Startup Integration Group
        system_group = Adw.PreferencesGroup()
        system_group.set_title("Desktop & Startup Integration")
        self.add(system_group)

        # Desktop Autostart on Login
        autostart_row = Adw.SwitchRow()
        autostart_row.set_title("Launch Tray on Desktop Login")
        autostart_row.set_subtitle("Automatically start system tray icon on user login")
        autostart_row.set_active(is_autostart_enabled())

        def _on_autostart_change(row, gparam):
            if row.get_active():
                enable_autostart()
            else:
                disable_autostart()

        autostart_row.connect("notify::active", _on_autostart_change)
        system_group.add(autostart_row)

        # Background systemd Timer
        sysd_status = self.svc_mgr.get_status()
        service_row = Adw.SwitchRow()
        service_row.set_title("Background systemd Timer")
        service_row.set_subtitle("Automatic background rotation via systemd user timer")
        service_row.set_active(bool(sysd_status.get("timer_active") or sysd_status.get("timer_enabled")))

        def _on_service_change(row, gparam):
            if row.get_active():
                self.svc_mgr.install(
                    interval_minutes=sched_cfg.get("interval_minutes", 5),
                    on_boot=sched_cfg.get("on_boot", True),
                )
            else:
                self.svc_mgr.uninstall()

        service_row.connect("notify::active", _on_service_change)
        system_group.add(service_row)

        # Application Menu Launcher Entry
        app_row = Adw.SwitchRow()
        app_row.set_title("Application Menu Shortcut")
        app_row.set_subtitle("Show awall in Linux application launcher menus and app grid")
        app_row.set_active(is_desktop_app_installed())

        def _on_app_menu_change(row, gparam):
            if row.get_active():
                install_desktop_app()
            else:
                uninstall_desktop_app()

        app_row.connect("notify::active", _on_app_menu_change)
        system_group.add(app_row)

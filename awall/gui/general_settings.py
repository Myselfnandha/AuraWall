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

        focus_row = Adw.SwitchRow()
        focus_row.set_title("Smart Pause on Active Application")
        focus_row.set_subtitle("Pause rotation while using apps, change immediately when returning to desktop")
        focus_row.set_active(sched_cfg.get("pause_on_active_window", True))

        def _on_focus_change(row, gparam):
            sched_cfg["pause_on_active_window"] = row.get_active()
            self.on_change()

        focus_row.connect("notify::active", _on_focus_change)
        sched_group.add(focus_row)

        # 2. Display and Transitions Group
        disp_cfg = self.config.setdefault("display", {})
        disp_group = Adw.PreferencesGroup()
        disp_group.set_title("Display and Visual Effects")
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

        # 3. Multi-Monitor Displays Group
        from awall.monitor import get_monitors

        mon_group = Adw.PreferencesGroup()
        mon_group.set_title("Multi-Monitor Displays")
        self.add(mon_group)

        multi_mode_row = Adw.ComboRow()
        multi_mode_row.set_title("Multi-Monitor Mode")
        multi_mode_row.set_subtitle("Choose whether displays share one wallpaper or have unique wallpapers")
        multi_model = Gtk.StringList()
        multi_model.append("Unified (Same Wallpaper on All)")
        multi_model.append("Per-Monitor (Unique Wallpapers)")
        multi_mode_row.set_model(multi_model)

        curr_multi = disp_cfg.get("multi_monitor", "unified")
        multi_mode_row.set_selected(1 if curr_multi == "per_monitor" else 0)

        def _on_multi_change(row, gparam):
            disp_cfg["multi_monitor"] = "per_monitor" if row.get_selected() == 1 else "unified"
            self.on_change()

        multi_mode_row.connect("notify::selected", _on_multi_change)
        mon_group.add(multi_mode_row)

        # Dynamic per-monitor rows
        detected_monitors = get_monitors()
        mon_config_dict = disp_cfg.setdefault("monitor_config", {})

        for mon in detected_monitors:
            mon_row = Adw.ComboRow()
            mon_title = f"Display: {mon.name}"
            if mon.is_primary:
                mon_title += " ★ Primary"
            mon_row.set_title(mon_title)
            mon_row.set_subtitle(f"Resolution: {mon.width}×{mon.height}")

            per_mon_model = Gtk.StringList()
            per_mon_model.append("Unique Wallpaper (Rotate Independently)")
            per_mon_model.append("Shared (Mirror Primary Wallpaper)")
            mon_row.set_model(per_mon_model)

            cur_mode = mon_config_dict.get(mon.name, {}).get("mode", "unique")
            mon_row.set_selected(1 if cur_mode == "shared" else 0)

            def _make_mon_handler(m_name):
                def _on_mon_mode_change(row, gparam):
                    m_cfg = mon_config_dict.setdefault(m_name, {})
                    m_cfg["mode"] = "shared" if row.get_selected() == 1 else "unique"
                    self.on_change()
                return _on_mon_mode_change

            mon_row.connect("notify::selected", _make_mon_handler(mon.name))
            mon_group.add(mon_row)

        # 4. Lock Screen Synchronization Group
        lock_cfg = disp_cfg.setdefault("lock_screen", {})
        lock_group = Adw.PreferencesGroup()
        lock_group.set_title("Lock Screen Synchronization")
        self.add(lock_group)

        lock_sync_row = Adw.SwitchRow()
        lock_sync_row.set_title("Sync Wallpaper to Lock Screen")
        lock_sync_row.set_subtitle("Automatically update lock screen background to match desktop wallpaper")
        lock_sync_row.set_active(lock_cfg.get("enabled", True))

        def _on_lock_sync_change(row, gparam):
            lock_cfg["enabled"] = row.get_active()
            self.on_change()

        lock_sync_row.connect("notify::active", _on_lock_sync_change)
        lock_group.add(lock_sync_row)

        # Rotate on Sign-in / Unlock toggle
        unlock_rotate_row = Adw.SwitchRow()
        unlock_rotate_row.set_title("Rotate Lock Screen on Sign-in / Unlock")
        unlock_rotate_row.set_subtitle("Change the lock screen wallpaper once every time you unlock or sign in")
        unlock_rotate_row.set_active(lock_cfg.get("rotate_on_unlock", True))

        def _on_unlock_rotate_change(row, gparam):
            lock_cfg["rotate_on_unlock"] = row.get_active()
            self.on_change()

        unlock_rotate_row.connect("notify::active", _on_unlock_rotate_change)
        lock_group.add(unlock_rotate_row)

        # Unlock rotation mode selector
        unlock_mode_row = Adw.ComboRow()
        unlock_mode_row.set_title("Unlock Rotation Strategy")
        unlock_mode_row.set_subtitle("How to select the new lock screen wallpaper on sign-in")
        unlock_model = Gtk.StringList()
        unlock_modes = [
            ("independent", "Independent New Wallpaper (Fresh Image)"),
            ("sync_desktop", "Sync with Desktop Wallpaper (Rotate Both)"),
            ("favorites_cache", "Pick from Favorites & Local Cache"),
        ]
        for _, u_label in unlock_modes:
            unlock_model.append(u_label)
        unlock_mode_row.set_model(unlock_model)

        u_keys = [k for k, _ in unlock_modes]
        cur_um = lock_cfg.get("unlock_mode", "independent")
        unlock_mode_row.set_selected(u_keys.index(cur_um) if cur_um in u_keys else 0)

        def _on_unlock_mode_change(row, gparam):
            sel = row.get_selected()
            if 0 <= sel < len(u_keys):
                lock_cfg["unlock_mode"] = u_keys[sel]
                self.on_change()

        unlock_mode_row.connect("notify::selected", _on_unlock_mode_change)
        lock_group.add(unlock_mode_row)

        effect_row = Adw.ComboRow()
        effect_row.set_title("Lock Screen Visual Effect")
        effect_row.set_subtitle("Apply blur or dark dimming overlay for better lock dialog readability")
        effect_model = Gtk.StringList()
        effects = [
            ("none", "None (Original Wallpaper)"),
            ("blur", "Gaussian Blur"),
            ("dim", "Dim Overlay (Darkened)"),
            ("blur_dim", "Gaussian Blur + Dimming"),
        ]
        for _, eff_label in effects:
            effect_model.append(eff_label)
        effect_row.set_model(effect_model)

        eff_keys = [k for k, _ in effects]
        cur_eff = lock_cfg.get("effect", "none")
        effect_row.set_selected(eff_keys.index(cur_eff) if cur_eff in eff_keys else 0)

        def _on_effect_change(row, gparam):
            sel = row.get_selected()
            if 0 <= sel < len(eff_keys):
                lock_cfg["effect"] = eff_keys[sel]
                self.on_change()

        effect_row.connect("notify::selected", _on_effect_change)
        lock_group.add(effect_row)

        blur_spin = Adw.SpinRow.new_with_range(1, 30, 1)
        blur_spin.set_title("Gaussian Blur Radius")
        blur_spin.set_subtitle("Amount of background blur applied to lock screen (1–30)")
        blur_spin.set_value(float(lock_cfg.get("blur_radius", 15)))

        def _on_blur_change(row, gparam):
            lock_cfg["blur_radius"] = int(row.get_value())
            self.on_change()

        blur_spin.connect("notify::value", _on_blur_change)
        lock_group.add(blur_spin)

        dim_spin = Adw.SpinRow.new_with_range(0.1, 0.9, 0.05)
        dim_spin.set_title("Dimming Opacity")
        dim_spin.set_subtitle("Darkness percentage of dim overlay (10%–90%)")
        dim_spin.set_value(float(lock_cfg.get("dim_opacity", 0.4)))

        def _on_dim_change(row, gparam):
            lock_cfg["dim_opacity"] = round(float(row.get_value()), 2)
            self.on_change()

        dim_spin.connect("notify::value", _on_dim_change)
        lock_group.add(dim_spin)

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

        open_cache_row = Adw.ActionRow()
        open_cache_row.set_title("Open Cache Folder")
        open_cache_row.set_subtitle("Browse downloaded and cached wallpapers in file manager")
        open_cache_btn = Gtk.Button(label="Open Folder")
        open_cache_btn.set_valign(Gtk.Align.CENTER)
        open_cache_btn.add_css_class("flat")

        def _on_open_cache_click(_):
            import subprocess
            from awall.cache import get_default_cache_dir
            try:
                subprocess.Popen(["xdg-open", str(get_default_cache_dir())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        open_cache_btn.connect("clicked", _on_open_cache_click)
        open_cache_row.add_suffix(open_cache_btn)
        cache_group.add(open_cache_row)

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

        # 5. Desktop and Startup Integration Group
        system_group = Adw.PreferencesGroup()
        system_group.set_title("Desktop and Startup Integration")
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

        # Config Folder Row
        open_config_row = Adw.ActionRow()
        open_config_row.set_title("Configuration Directory")
        open_config_row.set_subtitle("Open ~/.config/auto_wall in file manager")
        open_config_btn = Gtk.Button(label="Open Config")
        open_config_btn.set_valign(Gtk.Align.CENTER)
        open_config_btn.add_css_class("flat")

        def _on_open_config_click(_):
            import subprocess
            from awall.config import get_config_dir
            try:
                subprocess.Popen(["xdg-open", str(get_config_dir())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        open_config_btn.connect("clicked", _on_open_config_click)
        open_config_row.add_suffix(open_config_btn)
        system_group.add(open_config_row)

"""
Desktop overlay widgets settings page for GTK4/Libadwaita GUI.
"""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk
from typing import Any, Dict


class WidgetSettingsPage(Adw.PreferencesPage):
    """Settings page for compositing digital clock, weather, media player, and quotes."""

    def __init__(self, config: Dict[str, Any], on_change_callback):
        super().__init__()
        self.set_title("Widgets")
        self.set_icon_name("preferences-desktop-display-symbolic")
        self.config = config
        self.on_change = on_change_callback

        self._build_ui()

    def _build_ui(self):
        w_cfg = self.config.setdefault("widgets", {})

        # 1. Main Toggle Group
        main_group = Adw.PreferencesGroup()
        main_group.set_title("Desktop Overlay Widgets")
        main_group.set_description("Composites live aesthetic widgets directly onto your wallpaper.")
        self.add(main_group)

        enable_switch = Adw.SwitchRow()
        enable_switch.set_title("Enable Desktop Widgets")
        enable_switch.set_subtitle("Overlay digital clock, live weather, and media info")
        enable_switch.set_active(w_cfg.get("enabled", False))

        def _on_enable_toggle(row, gparam):
            w_cfg["enabled"] = row.get_active()
            self.on_change()

        enable_switch.connect("notify::active", _on_enable_toggle)
        main_group.add(enable_switch)

        # Position Preset
        pos_row = Adw.ComboRow()
        pos_row.set_title("Widget Placement")
        pos_model = Gtk.StringList()
        positions = [
            ("Centered (Hero Clock)", "center"),
            ("Top Center", "top_center"),
            ("Bottom Center", "bottom_center"),
            ("Top Left", "top_left"),
            ("Top Right", "top_right"),
            ("Bottom Left", "bottom_left"),
            ("Bottom Right", "bottom_right"),
        ]
        for label, _ in positions:
            pos_model.append(label)
        pos_row.set_model(pos_model)

        curr_pos = w_cfg.get("position", "center")
        pos_idx = 0
        for i, (_, val) in enumerate(positions):
            if val == curr_pos:
                pos_idx = i
        pos_row.set_selected(pos_idx)

        def _on_pos_change(row, gparam):
            sel = row.get_selected()
            if 0 <= sel < len(positions):
                w_cfg["position"] = positions[sel][1]
                self.on_change()

        pos_row.connect("notify::selected", _on_pos_change)
        main_group.add(pos_row)

        # 2. Included Widget Elements
        elements_group = Adw.PreferencesGroup()
        elements_group.set_title("Widget Components")
        self.add(elements_group)

        # Clock & Date
        clock_switch = Adw.SwitchRow()
        clock_switch.set_title("Digital Clock & Date")
        clock_switch.set_active(w_cfg.get("show_clock", True))

        def _on_clock_toggle(row, gparam):
            w_cfg["show_clock"] = row.get_active()
            self.on_change()

        clock_switch.connect("notify::active", _on_clock_toggle)
        elements_group.add(clock_switch)

        # Live Weather
        weather_switch = Adw.SwitchRow()
        weather_switch.set_title("Live Weather Badge")
        weather_switch.set_active(w_cfg.get("show_weather", True))

        def _on_weather_toggle(row, gparam):
            w_cfg["show_weather"] = row.get_active()
            self.on_change()

        weather_switch.connect("notify::active", _on_weather_toggle)
        elements_group.add(weather_switch)

        # Music Player
        media_switch = Adw.SwitchRow()
        media_switch.set_title("Currently Playing Music (MPRIS)")
        media_switch.set_active(w_cfg.get("show_media", True))

        def _on_media_toggle(row, gparam):
            w_cfg["show_media"] = row.get_active()
            self.on_change()

        media_switch.connect("notify::active", _on_media_toggle)
        elements_group.add(media_switch)

        # Daily Quotes
        quote_switch = Adw.SwitchRow()
        quote_switch.set_title("Daily Inspirational Quote")
        quote_switch.set_active(w_cfg.get("show_quote", False))

        def _on_quote_toggle(row, gparam):
            w_cfg["show_quote"] = row.get_active()
            self.on_change()

        quote_switch.connect("notify::active", _on_quote_toggle)
        elements_group.add(quote_switch)

        # Translucent Backdrop
        backdrop_switch = Adw.SwitchRow()
        backdrop_switch.set_title("Glassmorphic Backdrop Box")
        backdrop_switch.set_subtitle("Translucent background panel for high contrast readability")
        backdrop_switch.set_active(w_cfg.get("backdrop", True))

        def _on_backdrop_toggle(row, gparam):
            w_cfg["backdrop"] = row.get_active()
            self.on_change()

        backdrop_switch.connect("notify::active", _on_backdrop_toggle)
        elements_group.add(backdrop_switch)

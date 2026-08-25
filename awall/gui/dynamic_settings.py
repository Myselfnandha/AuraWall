"""
Dynamic solar & live weather settings page for GTK4/Libadwaita GUI.
"""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk
from typing import Any, Dict


class DynamicSettingsPage(Adw.PreferencesPage):
    """Settings page for solar elevation, live weather matching, and location."""

    def __init__(self, config: Dict[str, Any], on_change_callback):
        super().__init__()
        self.set_title("Dynamic and Weather")
        self.set_icon_name("weather-clear-symbolic")
        self.config = config
        self.on_change = on_change_callback

        self._build_ui()

    def _build_ui(self):
        dyn_cfg = self.config.setdefault("dynamic", {})

        # 1. Main Toggle Group
        main_group = Adw.PreferencesGroup()
        main_group.set_title("Dynamic Wallpaper Mode")
        main_group.set_description("Automatically matches wallpaper lighting and mood with current solar time and live weather.")
        self.add(main_group)

        dyn_switch = Adw.SwitchRow()
        dyn_switch.set_title("Enable Dynamic Wallpapers")
        dyn_switch.set_subtitle("Synthesize search keywords matching sun and climate")
        dyn_switch.set_active(dyn_cfg.get("enabled", True))

        def _on_dyn_toggle(row, gparam):
            dyn_cfg["enabled"] = row.get_active()
            self.on_change()

        dyn_switch.connect("notify::active", _on_dyn_toggle)
        main_group.add(dyn_switch)

        solar_switch = Adw.SwitchRow()
        solar_switch.set_title("Solar Position and Time of Day")
        solar_switch.set_subtitle("Dawn, Sunrise, Noon, Golden Hour, Sunset, Night")
        solar_switch.set_active(dyn_cfg.get("use_solar", True))

        def _on_solar_toggle(row, gparam):
            dyn_cfg["use_solar"] = row.get_active()
            self.on_change()

        solar_switch.connect("notify::active", _on_solar_toggle)
        main_group.add(solar_switch)

        wtr_switch = Adw.SwitchRow()
        wtr_switch.set_title("Live Weather Sync")
        wtr_switch.set_subtitle("Sync mood with Open-Meteo (Rain, Snow, Clouds, Clear)")
        wtr_switch.set_active(dyn_cfg.get("use_weather", True))

        def _on_wtr_toggle(row, gparam):
            dyn_cfg["use_weather"] = row.get_active()
            self.on_change()

        wtr_switch.connect("notify::active", _on_wtr_toggle)
        main_group.add(wtr_switch)

        # 2. Location Group
        loc_group = Adw.PreferencesGroup()
        loc_group.set_title("Location and Coordinates")
        loc_group.set_description("Leave empty to use automatic IP geolocation.")
        self.add(loc_group)

        city_row = Adw.EntryRow()
        city_row.set_title("City Name (Optional)")
        city_row.set_text(dyn_cfg.get("city", ""))

        def _on_city_change(row):
            dyn_cfg["city"] = row.get_text().strip()
            self.on_change()

        city_row.connect("changed", _on_city_change)
        loc_group.add(city_row)

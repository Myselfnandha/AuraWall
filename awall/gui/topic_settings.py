"""
Topic and category configuration panel for GTK4/Libadwaita GUI.
"""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk
from typing import Any, Dict, List

from awall.config import ALL_TOPICS


class TopicSettingsPage(Adw.PreferencesPage):
    """Settings page for enabling and customizing wallpaper topic categories."""

    def __init__(self, config: Dict[str, Any], on_change_callback):
        super().__init__()
        self.set_title("Topics")
        self.set_icon_name("view-list-bullet-symbolic")
        self.config = config
        self.on_change = on_change_callback
        self.switch_rows = {}

        self._build_ui()

    def _build_ui(self):
        topics_cfg = self.config.setdefault("topics", {})
        enabled_topics = set(topics_cfg.setdefault("enabled", list(ALL_TOPICS)))

        # Mode Selection
        mode_group = Adw.PreferencesGroup()
        mode_group.set_title("Topic Selection Mode")
        self.add(mode_group)

        mode_row = Adw.ComboRow()
        mode_row.set_title("Rotation Mode")
        model = Gtk.StringList()
        model.append("Mixed (Random category)")
        model.append("Sequential (Cycle one by one)")
        mode_row.set_model(model)

        curr_mode = topics_cfg.get("mode", "mixed")
        mode_row.set_selected(0 if curr_mode == "mixed" else 1)

        def _on_mode_change(row, gparam):
            topics_cfg["mode"] = "mixed" if row.get_selected() == 0 else "sequential"
            self.on_change()

        mode_row.connect("notify::selected", _on_mode_change)
        mode_group.add(mode_row)

        # Categories list
        cat_group = Adw.PreferencesGroup()
        cat_group.set_title("Enabled Categories")
        cat_group.set_description("Toggle which wallpaper categories to include.")
        self.add(cat_group)

        for topic in ALL_TOPICS:
            clean_name = topic.replace("_", " ").title()
            row = Adw.SwitchRow()
            row.set_title(clean_name)
            is_active = topic in enabled_topics
            row.set_active(is_active)

            def _create_handler(t_name):
                def _handler(switch_row, gparam):
                    current_enabled = self.config["topics"].setdefault("enabled", [])
                    if switch_row.get_active():
                        if t_name not in current_enabled:
                            current_enabled.append(t_name)
                    else:
                        if t_name in current_enabled:
                            current_enabled.remove(t_name)
                    self.on_change()
                return _handler

            row.connect("notify::active", _create_handler(topic))
            self.switch_rows[topic] = row
            cat_group.add(row)

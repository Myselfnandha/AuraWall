"""
Main window implementation for GTK4/Libadwaita settings application.
"""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from awall.config import load_config, save_config
from awall.daemon import change_wallpaper
from awall.gui.dynamic_settings import DynamicSettingsPage
from awall.gui.gallery_page import GalleryPage
from awall.gui.general_settings import GeneralSettingsPage
from awall.gui.source_settings import SourceSettingsPage
from awall.gui.topic_settings import TopicSettingsPage
from awall.history import HistoryManager


class MainWindow(Adw.PreferencesWindow):
    """Main Adwaita Preferences Window for awall."""

    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("awall Wallpaper Engine")
        self.set_default_size(880, 740)

        self.config = load_config()
        self.history_mgr = HistoryManager()

        # Add Preferences Pages
        self.gallery_page = GalleryPage(self.config, self._on_config_changed)
        self.sources_page = SourceSettingsPage(self.config, self._on_config_changed)
        self.topics_page = TopicSettingsPage(self.config, self._on_config_changed)
        self.dynamic_page = DynamicSettingsPage(self.config, self._on_config_changed)
        self.general_page = GeneralSettingsPage(self.config, self._on_config_changed)

        self.add(self.gallery_page)
        self.add(self.sources_page)
        self.add(self.topics_page)
        self.add(self.dynamic_page)
        self.add(self.general_page)

    def _on_config_changed(self):
        """Auto-save config on any UI interaction and refresh gallery filter."""
        save_config(self.config)
        if hasattr(self, "gallery_page"):
            self.gallery_page.config = self.config
            self.gallery_page.load_gallery()

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
        self.set_default_size(920, 760)

        # Ensure titlebar displays minimize, maximize/restore, and close buttons on the top right
        try:
            gtk_settings = Gtk.Settings.get_default()
            if gtk_settings:
                gtk_settings.set_property("gtk-decoration-layout", ":minimize,maximize,close")
        except Exception:
            pass

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

        self._setup_headerbar_elements()

    def _setup_headerbar_elements(self):
        """Places the app name on the left of the search icon and minimize/maximize buttons to the left of close."""
        header_bar = None

        def find_header(w):
            nonlocal header_bar
            if isinstance(w, Adw.HeaderBar):
                header_bar = w
                return
            child = w.get_first_child()
            while child:
                find_header(child)
                child = child.get_next_sibling()

        find_header(self)
        if not header_bar:
            return

        # 1. Left side: App name and logo (to the left of search icon)
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_box.set_valign(Gtk.Align.CENTER)
        title_box.set_margin_start(10)
        title_box.set_margin_end(6)

        logo = Gtk.Image.new_from_icon_name("preferences-desktop-wallpaper-symbolic")
        title_lbl = Gtk.Label(label="awall")
        title_lbl.add_css_class("title-4")
        title_lbl.add_css_class("heading")

        title_box.append(logo)
        title_box.append(title_lbl)
        header_bar.pack_start(title_box)

        # 2. Right side: Minimize and Maximize/Restore buttons (to the left of close button)
        min_btn = Gtk.Button.new_from_icon_name("window-minimize-symbolic")
        min_btn.set_valign(Gtk.Align.CENTER)
        min_btn.add_css_class("flat")
        min_btn.set_tooltip_text("Minimize Window")
        min_btn.connect("clicked", lambda _: self.minimize())

        self.max_btn = Gtk.Button.new_from_icon_name("window-maximize-symbolic")
        self.max_btn.set_valign(Gtk.Align.CENTER)
        self.max_btn.add_css_class("flat")
        self.max_btn.set_tooltip_text("Maximize Window")

        def toggle_maximize(_):
            if self.is_maximized():
                self.unmaximize()
            else:
                self.maximize()

        self.max_btn.connect("clicked", toggle_maximize)

        # Sync maximize icon on window state changes
        def on_maximized_changed(win, _):
            if win.is_maximized():
                self.max_btn.set_icon_name("view-restore-symbolic")
                self.max_btn.set_tooltip_text("Restore Window Size")
            else:
                self.max_btn.set_icon_name("window-maximize-symbolic")
                self.max_btn.set_tooltip_text("Maximize Window")

        self.connect("notify::maximized", on_maximized_changed)

        # pack_end adds widgets from right to left, placing them directly left of close
        header_bar.pack_end(self.max_btn)
        header_bar.pack_end(min_btn)

    def _on_config_changed(self):
        """Auto-save config on any UI interaction and refresh gallery filter."""
        save_config(self.config)
        if hasattr(self, "gallery_page"):
            self.gallery_page.config = self.config
            self.gallery_page.load_gallery()

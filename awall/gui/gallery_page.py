"""
Gallery and Favorites visual browser page for GTK4/Libadwaita.
Displays a responsive thumbnail grid of cached and favorited wallpapers with 1-click preview and application.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from awall.cache import CacheManager
from awall.config import load_config
from awall.gui.preview_dialog import WallpaperPreviewDialog
from awall.history import HistoryManager


class WallpaperCard(Gtk.Button):
    """Interactive card item in the wallpaper grid."""

    def __init__(
        self,
        image_path: Path,
        history_entry: Optional[Dict[str, Any]],
        is_favorite: bool,
        on_click_callback: Callable[[Path, Optional[Dict[str, Any]]], None],
    ):
        super().__init__()
        self.image_path = image_path
        self.history_entry = history_entry
        self.is_fav = is_favorite
        self.on_click_cb = on_click_callback

        self.add_css_class("flat")
        self.set_valign(Gtk.Align.FILL)
        self.set_hexpand(True)

        self._build_ui()
        self.connect("clicked", self._on_clicked)

    def _build_ui(self):
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_box.add_css_class("card")
        card_box.set_margin_top(4)
        card_box.set_margin_bottom(4)
        card_box.set_margin_start(4)
        card_box.set_margin_end(4)

        # Overlay to place favorite star badge on top-right of image
        overlay = Gtk.Overlay()

        self.picture = Gtk.Picture()
        self.picture.set_content_fit(Gtk.ContentFit.COVER)
        self.picture.set_size_request(200, 125)
        self.picture.set_can_shrink(True)
        overlay.set_child(self.picture)

        # Favorite Star Badge
        if self.is_fav:
            star_icon = Gtk.Image.new_from_icon_name("starred-symbolic")
            star_icon.set_halign(Gtk.Align.END)
            star_icon.set_valign(Gtk.Align.START)
            star_icon.set_margin_top(6)
            star_icon.set_margin_end(6)
            star_icon.add_css_class("accent")
            overlay.add_overlay(star_icon)

        card_box.append(overlay)

        # Caption label
        title = ""
        if self.history_entry:
            title = self.history_entry.get("photographer") or self.history_entry.get("description", "")
        if not title:
            title = self.image_path.stem.replace("_", " ").title()

        # Truncate long titles
        if len(title) > 22:
            title = title[:20] + "…"

        label = Gtk.Label(label=title)
        label.set_halign(Gtk.Align.CENTER)
        label.set_margin_bottom(6)
        label.add_css_class("caption")
        card_box.append(label)

        self.set_child(card_box)

    def set_thumbnail_file(self, thumb_path: Path):
        """Sets the loaded thumbnail image."""
        if thumb_path.exists():
            file_obj = Gio.File.new_for_path(str(thumb_path))
            self.picture.set_file(file_obj)

    def _on_clicked(self, _):
        if self.on_click_cb:
            self.on_click_cb(self.image_path, self.history_entry)


class GalleryPage(Adw.PreferencesPage):
    """Preferences page featuring an interactive grid of cached and favorited wallpapers."""

    def __init__(self, config: Dict[str, Any], on_change_callback: Optional[Callable] = None):
        super().__init__()
        self.set_title("Gallery")
        self.set_icon_name("view-grid-symbolic")
        self.config = config
        self.on_change = on_change_callback

        self.cache_mgr = CacheManager()
        self.history_mgr = HistoryManager()
        self.cards: List[WallpaperCard] = []

        self._build_ui()
        self.load_gallery()

    def _build_ui(self):
        # Header Preferences Group
        self.header_group = Adw.PreferencesGroup()
        self.header_group.set_title("Wallpaper Library")
        self.header_group.set_description("Browse, preview, and apply downloaded wallpapers from your collection.")
        self.add(self.header_group)

        # Action bar row with Refresh & Cache stats
        action_row = Adw.ActionRow()
        self.stats_label = Gtk.Label()
        self.stats_label.add_css_class("dim-label")
        action_row.add_suffix(self.stats_label)

        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.set_valign(Gtk.Align.CENTER)
        refresh_btn.set_tooltip_text("Refresh Gallery")
        refresh_btn.connect("clicked", lambda _: self.load_gallery())
        action_row.add_suffix(refresh_btn)
        self.header_group.add(action_row)

        # Grid Group
        self.grid_group = Adw.PreferencesGroup()
        self.add(self.grid_group)

        # Responsive FlowBox Grid
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(4)
        self.flowbox.set_min_children_per_line(2)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_column_spacing(8)
        self.flowbox.set_row_spacing(8)
        self.flowbox.set_margin_top(8)
        self.flowbox.set_margin_bottom(12)

        self.grid_group.add(self.flowbox)

        # Status page placeholder for empty state
        self.empty_status = Adw.StatusPage()
        self.empty_status.set_icon_name("preferences-desktop-wallpaper-symbolic")
        self.empty_status.set_title("No Cached Wallpapers")
        self.empty_status.set_description("Wallpapers downloaded by awall will appear here automatically.")
        self.empty_status.set_visible(False)
        self.grid_group.add(self.empty_status)

    def load_gallery(self):
        """Discovers cached files and populates the grid."""
        # Clear existing children
        while True:
            child = self.flowbox.get_first_child()
            if not child:
                break
            self.flowbox.remove(child)

        self.cards.clear()

        cached_files = self.cache_mgr.get_cached_files()
        total_count = len(cached_files)
        _, total_mb = self.cache_mgr.get_stats()

        self.stats_label.set_label(f"{total_count} wallpapers ({total_mb:.1f} MB)")

        if not cached_files:
            self.empty_status.set_visible(True)
            self.flowbox.set_visible(False)
            return

        self.empty_status.set_visible(False)
        self.flowbox.set_visible(True)

        history_entries = self.history_mgr.get_history(limit=200)
        history_map = {Path(e.get("file_path", "")).resolve(): e for e in history_entries}

        # Create cards
        for f in cached_files:
            resolved_p = f.resolve()
            h_entry = history_map.get(resolved_p)
            is_fav = self.history_mgr.is_file_favorite(str(resolved_p))

            card = WallpaperCard(
                image_path=f,
                history_entry=h_entry,
                is_favorite=is_fav,
                on_click_callback=self._on_card_clicked,
            )
            self.cards.append(card)
            self.flowbox.append(card)

        # Asynchronously generate and populate thumbnails
        threading.Thread(target=self._load_thumbnails_worker, daemon=True).start()

    def _load_thumbnails_worker(self):
        """Worker thread that downscales thumbnails and dispatches to GTK."""
        for card in list(self.cards):
            thumb_path = self.cache_mgr.get_thumbnail(card.image_path, width=320, height=180)
            GLib.idle_add(card.set_thumbnail_file, thumb_path)

    def _on_card_clicked(self, image_path: Path, history_entry: Optional[Dict[str, Any]]):
        """Opens the modal preview dialog."""
        root_win = self.get_root()
        dialog = WallpaperPreviewDialog(
            parent=root_win,
            wallpaper_path=image_path,
            history_entry=history_entry,
            on_applied_callback=lambda p: self.load_gallery(),
            on_favorite_callback=lambda p, s: self.load_gallery(),
        )
        dialog.present()

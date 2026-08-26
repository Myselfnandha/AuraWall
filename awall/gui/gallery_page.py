"""
Gallery and Favorites visual browser page for GTK4/Libadwaita.
Displays a responsive thumbnail grid of cached and favorited wallpapers with real-time search,
automatic disk deduplication, disabled-sources filtering, and 1-click preview.
"""

from __future__ import annotations

import os
import re
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


def get_file_source(image_path: Path, history_entry: Optional[Dict[str, Any]]) -> str:
    """Hybrid detector identifying the source provider of a cached wallpaper."""
    if history_entry and history_entry.get("source") and history_entry.get("source") != "cache":
        return history_entry["source"].lower()

    name = image_path.name.lower()
    # Check for prefix matches like lock_bing_, test_wallhaven_, bing_, pexels_, etc.
    for src in ("wallhaven", "bing", "pexels", "unsplash", "pixabay", "reddit", "local"):
        if re.search(rf"(?:^|_){src}(?:_|\.|$)", name):
            return src

    return "local"


class WallpaperCard(Gtk.Button):
    """Interactive card item in the wallpaper grid."""

    def __init__(
        self,
        image_path: Path,
        history_entry: Optional[Dict[str, Any]],
        source_name: str,
        is_favorite: bool,
        on_click_callback: Callable[[Path, Optional[Dict[str, Any]]], None],
    ):
        super().__init__()
        self.image_path = image_path
        self.history_entry = history_entry
        self.source_name = source_name
        self.is_fav = is_favorite
        self.on_click_cb = on_click_callback

        # Search index cache string
        author = (history_entry.get("photographer") if history_entry else "") or ""
        desc = (history_entry.get("description") if history_entry else "") or ""
        topic = (history_entry.get("topic") if history_entry else "") or ""
        self.search_text = f"{author} {desc} {topic} {source_name} {image_path.name}".lower()

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
        self.picture.set_size_request(220, 135)
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

        if len(title) > 24:
            title = title[:22] + "…"

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

    def matches_query(self, query: str) -> bool:
        """Returns True if the card matches the search query terms."""
        if not query:
            return True
        terms = query.lower().split()
        return all(t in self.search_text for t in terms)

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

        # Toolbar Row: Search Entry + Stats + Window Controls
        toolbar_row = Adw.ActionRow()

        # Real-time Search Entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search by title, author, topic, or source...")
        self.search_entry.set_hexpand(True)
        self.search_entry.set_valign(Gtk.Align.CENTER)
        self.search_entry.connect("search-changed", self._on_search_changed)
        toolbar_row.add_prefix(self.search_entry)

        # Move / Drag Handle
        drag_btn = Gtk.Button.new_from_icon_name("view-more-horizontal-symbolic")
        drag_btn.set_valign(Gtk.Align.CENTER)
        drag_btn.set_tooltip_text("Drag to Move Window")
        drag_btn.add_css_class("flat")
        toolbar_row.add_suffix(drag_btn)

        # Stats Label
        self.stats_label = Gtk.Label()
        self.stats_label.add_css_class("dim-label")
        self.stats_label.set_valign(Gtk.Align.CENTER)
        toolbar_row.add_suffix(self.stats_label)

        # Refresh Button
        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.set_valign(Gtk.Align.CENTER)
        refresh_btn.set_tooltip_text("Refresh & Deduplicate Gallery")
        refresh_btn.connect("clicked", lambda _: self.load_gallery())
        toolbar_row.add_suffix(refresh_btn)

        # Minimize Button
        min_btn = Gtk.Button.new_from_icon_name("window-minimize-symbolic")
        min_btn.set_valign(Gtk.Align.CENTER)
        min_btn.set_tooltip_text("Minimize Window")
        min_btn.connect("clicked", self._on_minimize_clicked)
        toolbar_row.add_suffix(min_btn)

        # Maximize / Restore Toggle Button
        self.max_btn = Gtk.Button.new_from_icon_name("window-maximize-symbolic")
        self.max_btn.set_valign(Gtk.Align.CENTER)
        self.max_btn.set_tooltip_text("Maximize Window")
        self.max_btn.connect("clicked", self._on_maximize_toggle_clicked)
        toolbar_row.add_suffix(self.max_btn)

        # Wrap in WindowHandle for native click-and-drag window movement
        handle = Gtk.WindowHandle()
        handle.set_child(toolbar_row)
        self.header_group.add(handle)

        self.connect("realize", lambda _: self._sync_window_state())

        # Grid Group
        self.grid_group = Adw.PreferencesGroup()
        self.add(self.grid_group)

        # Responsive Fluid FlowBox Grid (scales 2 to 6+ columns on resize / maximize)
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(8)
        self.flowbox.set_min_children_per_line(2)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_column_spacing(10)
        self.flowbox.set_row_spacing(10)
        self.flowbox.set_margin_top(8)
        self.flowbox.set_margin_bottom(16)

        self.grid_group.add(self.flowbox)

        # Status page placeholder for empty state
        self.empty_status = Adw.StatusPage()
        self.empty_status.set_icon_name("preferences-desktop-wallpaper-symbolic")
        self.empty_status.set_title("No Cached Wallpapers Found")
        self.empty_status.set_description("Wallpapers downloaded by awall will appear here automatically.")
        self.empty_status.set_visible(False)
        self.grid_group.add(self.empty_status)

    def load_gallery(self):
        """Discovers cached files, deduplicates disk cache, applies source filters, and populates the grid."""
        # 1. Clean up duplicate files from disk
        self.cache_mgr.deduplicate_cache()

        # Clear existing children
        while True:
            child = self.flowbox.get_first_child()
            if not child:
                break
            self.flowbox.remove(child)

        self.cards.clear()

        cached_files = self.cache_mgr.get_cached_files()
        history_entries = self.history_mgr.get_history(limit=500)
        history_map = {Path(e.get("file_path", "")).resolve(): e for e in history_entries}

        sources_cfg = self.config.get("sources", {})

        # Filter and create cards
        for f in cached_files:
            resolved_p = f.resolve()
            h_entry = history_map.get(resolved_p)
            src_name = get_file_source(f, h_entry)

            # Skip if source is disabled in settings
            if sources_cfg.get(src_name, {}).get("enabled") is False:
                continue

            is_fav = self.history_mgr.is_file_favorite(str(resolved_p))

            card = WallpaperCard(
                image_path=f,
                history_entry=h_entry,
                source_name=src_name,
                is_favorite=is_fav,
                on_click_callback=self._on_card_clicked,
            )
            self.cards.append(card)
            self.flowbox.append(card)

        total_count = len(self.cards)
        _, total_mb = self.cache_mgr.get_stats()
        self.stats_label.set_label(f"{total_count} wallpapers ({total_mb:.1f} MB)")

        if not self.cards:
            self.empty_status.set_visible(True)
            self.flowbox.set_visible(False)
            return

        self.empty_status.set_visible(False)
        self.flowbox.set_visible(True)

        # Apply any active search filter
        self._filter_cards()

        # Asynchronously generate and populate thumbnails
        threading.Thread(target=self._load_thumbnails_worker, daemon=True).start()

    def _on_search_changed(self, entry: Gtk.SearchEntry):
        """Filters cards in real-time as the user types."""
        self._filter_cards()

    def _filter_cards(self):
        """Applies visibility filter based on search query."""
        query = self.search_entry.get_text().strip()
        visible_count = 0

        for card in self.cards:
            matches = card.matches_query(query)
            card.set_visible(matches)
            if matches:
                visible_count += 1

        if visible_count == 0 and self.cards:
            self.empty_status.set_title("No Matching Wallpapers")
            self.empty_status.set_description(f"No wallpapers found matching '{query}'")
            self.empty_status.set_visible(True)
            self.flowbox.set_visible(False)
        else:
            self.empty_status.set_visible(False)
            self.flowbox.set_visible(True)

    def _load_thumbnails_worker(self):
        """Worker thread that downscales thumbnails and dispatches to GTK."""
        for card in list(self.cards):
            thumb_path = self.cache_mgr.get_thumbnail(card.image_path, width=320, height=180)
            GLib.idle_add(card.set_thumbnail_file, thumb_path)

    def _on_minimize_clicked(self, _):
        """Minimizes the root window."""
        root_win = self.get_root()
        if root_win and hasattr(root_win, "minimize"):
            root_win.minimize()

    def _on_maximize_toggle_clicked(self, _):
        """Toggles maximization of the root window."""
        root_win = self.get_root()
        if not root_win:
            return
        if hasattr(root_win, "is_maximized") and root_win.is_maximized():
            root_win.unmaximize()
            self.max_btn.set_icon_name("window-maximize-symbolic")
            self.max_btn.set_tooltip_text("Maximize Window")
        else:
            root_win.maximize()
            self.max_btn.set_icon_name("view-restore-symbolic")
            self.max_btn.set_tooltip_text("Restore Window Size")

    def _sync_window_state(self):
        """Connects to root window maximize state changes to keep button icon synced."""
        root_win = self.get_root()
        if root_win and not getattr(self, "_win_connected", False):
            self._win_connected = True
            root_win.connect("notify::maximized", self._on_win_maximized_changed)
            if hasattr(root_win, "is_maximized") and root_win.is_maximized():
                self.max_btn.set_icon_name("view-restore-symbolic")
                self.max_btn.set_tooltip_text("Restore Window Size")

    def _on_win_maximized_changed(self, win, _):
        """Callback for root window maximize notification."""
        if win.is_maximized():
            self.max_btn.set_icon_name("view-restore-symbolic")
            self.max_btn.set_tooltip_text("Restore Window Size")
        else:
            self.max_btn.set_icon_name("window-maximize-symbolic")
            self.max_btn.set_tooltip_text("Maximize Window")

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

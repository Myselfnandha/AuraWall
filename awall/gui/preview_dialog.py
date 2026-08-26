"""
Minimalist Modal Wallpaper Preview Dialog for GTK4/Libadwaita.
Shows large image preview, photographer attribution, and Apply to Desktop action.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from awall.history import HistoryManager
from awall.wallpaper_setter import set_wallpaper


class WallpaperPreviewDialog(Adw.Window):
    """Clean minimalist preview dialog for inspecting and applying a wallpaper."""

    def __init__(
        self,
        parent: Gtk.Window,
        wallpaper_path: Path,
        history_entry: Optional[Dict[str, Any]] = None,
        on_applied_callback: Optional[Callable[[Path], None]] = None,
        on_favorite_callback: Optional[Callable[[Path, bool], None]] = None,
    ):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(680, 560)
        self.set_title("Wallpaper Preview")

        self.wallpaper_path = Path(wallpaper_path).resolve()
        self.history_mgr = HistoryManager()
        self.history_entry = history_entry or {}
        self.on_applied = on_applied_callback
        self.on_favorite = on_favorite_callback

        self._build_ui()

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(main_box)

        # Header Bar
        header = Adw.HeaderBar()
        main_box.append(header)

        # Favorite Toggle Button in Header
        is_fav = self.history_mgr.is_file_favorite(str(self.wallpaper_path))
        self.fav_btn = Gtk.Button()
        self.fav_btn.set_icon_name("starred-symbolic" if is_fav else "non-starred-symbolic")
        self.fav_btn.set_tooltip_text("Favorite Wallpaper" if not is_fav else "Unfavorite Wallpaper")
        self.fav_btn.connect("clicked", self._on_toggle_favorite)
        header.pack_end(self.fav_btn)

        # Content Box with Margins
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(20)
        content_box.set_margin_start(20)
        content_box.set_margin_end(20)
        content_box.set_vexpand(True)
        main_box.append(content_box)

        # Large Picture Preview
        picture_frame = Gtk.Frame()
        picture_frame.set_vexpand(True)
        picture_frame.set_hexpand(True)
        picture_frame.add_css_class("card")

        self.picture = Gtk.Picture()
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.picture.set_can_shrink(True)
        if self.wallpaper_path.exists():
            file_obj = Gio.File.new_for_path(str(self.wallpaper_path))
            self.picture.set_file(file_obj)

        picture_frame.set_child(self.picture)
        content_box.append(picture_frame)

        # Info & Attribution Bar
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        info_box.set_valign(Gtk.Align.CENTER)

        # Metadata labels
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)

        photographer = self.history_entry.get("photographer")
        if not photographer:
            # Format filename if metadata not in history
            photographer = self.wallpaper_path.stem.replace("_", " ").title()

        source_name = self.history_entry.get("source", "local").title()

        title_label = Gtk.Label(label=photographer)
        title_label.set_halign(Gtk.Align.START)
        title_label.add_css_class("title-4")
        text_box.append(title_label)

        sub_label = Gtk.Label(label=f"Source: {source_name} • {self.wallpaper_path.name}")
        sub_label.set_halign(Gtk.Align.START)
        sub_label.add_css_class("caption")
        sub_label.add_css_class("dim-label")
        text_box.append(sub_label)

        info_box.append(text_box)

        # Apply to Desktop Button
        self.apply_btn = Gtk.Button(label="Apply to Desktop")
        self.apply_btn.add_css_class("suggested-action")
        self.apply_btn.add_css_class("pill")
        self.apply_btn.set_valign(Gtk.Align.CENTER)
        self.apply_btn.connect("clicked", self._on_apply_desktop)
        info_box.append(self.apply_btn)

        content_box.append(info_box)

    def _on_toggle_favorite(self, btn: Gtk.Button):
        is_fav = self.history_mgr.is_file_favorite(str(self.wallpaper_path))
        new_state = not is_fav
        self.history_mgr.mark_favorite(str(self.wallpaper_path), is_fav=new_state)
        btn.set_icon_name("starred-symbolic" if new_state else "non-starred-symbolic")
        btn.set_tooltip_text("Unfavorite Wallpaper" if new_state else "Favorite Wallpaper")
        if self.on_favorite:
            self.on_favorite(self.wallpaper_path, new_state)

    def _on_apply_desktop(self, btn: Gtk.Button):
        btn.set_sensitive(False)
        btn.set_label("Applying...")

        # Apply wallpaper in background thread
        def _worker():
            ok = set_wallpaper(self.wallpaper_path)
            if ok:
                # Add to history
                self.history_mgr.add_entry(
                    source=self.history_entry.get("source", "cache"),
                    file_path=str(self.wallpaper_path),
                    url=self.history_entry.get("url", ""),
                    photographer=self.history_entry.get("photographer", "Custom Wallpaper"),
                    photographer_url=self.history_entry.get("photographer_url", ""),
                    topic=self.history_entry.get("topic", "gallery"),
                )
            GLib.idle_add(self._on_applied_done, ok)

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def _on_applied_done(self, ok: bool):
        if ok:
            self.apply_btn.set_label("✓ Applied!")
            self.apply_btn.remove_css_class("suggested-action")
            self.apply_btn.add_css_class("success")
            if self.on_applied:
                self.on_applied(self.wallpaper_path)
            # Close dialog shortly after applying
            GLib.timeout_add(700, self.close)
        else:
            self.apply_btn.set_sensitive(True)
            self.apply_btn.set_label("Apply to Desktop")

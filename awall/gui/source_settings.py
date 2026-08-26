"""
Sources configuration panel for GTK4/Libadwaita GUI.
"""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk
from typing import Any, Dict


class SourceSettingsPage(Adw.PreferencesPage):
    """Settings page for enabling, configuring, and reordering wallpaper sources."""

    def __init__(self, config: Dict[str, Any], on_change_callback):
        super().__init__()
        self.set_title("Sources")
        self.set_icon_name("network-wired-symbolic")
        self.config = config
        self.on_change = on_change_callback

        self._build_ui()

    def _build_ui(self):
        sources_cfg = self.config.setdefault("sources", {})
        sources_group = Adw.PreferencesGroup()
        sources_group.set_title("Wallpaper Providers")
        sources_group.set_description("Enable sources and configure API keys or local folders.")
        self.add(sources_group)

        # 1. Wallhaven Row
        wallhaven_cfg = sources_cfg.setdefault("wallhaven", {"enabled": True, "api_key": ""})
        wallhaven_exp = Adw.ExpanderRow()
        wallhaven_exp.set_title("Wallhaven")
        wallhaven_exp.set_subtitle("4K and 8K digital art and photography (Free, no key required)")
        wallhaven_exp.set_show_enable_switch(True)
        wallhaven_exp.set_enable_expansion(wallhaven_cfg.get("enabled", True))

        def _toggle_wallhaven(row, gparam):
            wallhaven_cfg["enabled"] = row.get_enable_expansion()
            self.on_change()

        wallhaven_exp.connect("notify::enable-expansion", _toggle_wallhaven)

        wallhaven_key_row = Adw.EntryRow()
        wallhaven_key_row.set_title("API Key (Optional)")
        wallhaven_key_row.set_text(wallhaven_cfg.get("api_key", ""))

        def _change_wallhaven_key(row):
            wallhaven_cfg["api_key"] = row.get_text().strip()
            self.on_change()

        wallhaven_key_row.connect("changed", _change_wallhaven_key)
        wallhaven_exp.add_row(wallhaven_key_row)
        sources_group.add(wallhaven_exp)

        # 2. Bing Daily Row
        bing_cfg = sources_cfg.setdefault("bing", {"enabled": True})
        bing_exp = Adw.ActionRow()
        bing_exp.set_title("Bing Daily Wallpaper")
        bing_exp.set_subtitle("Daily curated ultra HD photography from Microsoft Bing (No key required)")
        bing_switch = Gtk.Switch()
        bing_switch.set_valign(Gtk.Align.CENTER)
        bing_switch.set_active(bing_cfg.get("enabled", True))

        def _toggle_bing(switch, gparam):
            bing_cfg["enabled"] = switch.get_active()
            self.on_change()

        bing_switch.connect("notify::active", _toggle_bing)
        bing_exp.add_suffix(bing_switch)
        sources_group.add(bing_exp)

        # 3. Unsplash Row
        unsplash_cfg = sources_cfg.setdefault("unsplash", {"enabled": True, "api_key": ""})
        unsplash_exp = Adw.ExpanderRow()
        unsplash_exp.set_title("Unsplash")
        unsplash_exp.set_subtitle("High quality curated photography")
        unsplash_exp.set_show_enable_switch(True)
        unsplash_exp.set_enable_expansion(unsplash_cfg.get("enabled", True))

        def _toggle_unsplash(row, gparam):
            unsplash_cfg["enabled"] = row.get_enable_expansion()
            self.on_change()

        unsplash_exp.connect("notify::enable-expansion", _toggle_unsplash)

        unsplash_key_row = Adw.EntryRow()
        unsplash_key_row.set_title("API Access Key (Optional)")
        unsplash_key_row.set_text(unsplash_cfg.get("api_key", ""))

        def _change_unsplash_key(row):
            unsplash_cfg["api_key"] = row.get_text().strip()
            self.on_change()

        unsplash_key_row.connect("changed", _change_unsplash_key)
        unsplash_exp.add_row(unsplash_key_row)
        sources_group.add(unsplash_exp)

        # 4. Pexels Row
        pexels_cfg = sources_cfg.setdefault("pexels", {"enabled": True, "api_key": ""})
        pexels_exp = Adw.ExpanderRow()
        pexels_exp.set_title("Pexels")
        pexels_exp.set_subtitle("Free stock photography and wallpaper collection")
        pexels_exp.set_show_enable_switch(True)
        pexels_exp.set_enable_expansion(pexels_cfg.get("enabled", True))

        def _toggle_pexels(row, gparam):
            pexels_cfg["enabled"] = row.get_enable_expansion()
            self.on_change()

        pexels_exp.connect("notify::enable-expansion", _toggle_pexels)

        pexels_key_row = Adw.EntryRow()
        pexels_key_row.set_title("API Key (Optional)")
        pexels_key_row.set_text(pexels_cfg.get("api_key", ""))

        def _change_pexels_key(row):
            pexels_cfg["api_key"] = row.get_text().strip()
            self.on_change()

        pexels_key_row.connect("changed", _change_pexels_key)
        pexels_exp.add_row(pexels_key_row)
        sources_group.add(pexels_exp)

        # 3. Pixabay Row
        pixabay_cfg = sources_cfg.setdefault("pixabay", {"enabled": True, "api_key": ""})
        pixabay_exp = Adw.ExpanderRow()
        pixabay_exp.set_title("Pixabay")
        pixabay_exp.set_subtitle("Vast collection of stock images and illustrations")
        pixabay_exp.set_show_enable_switch(True)
        pixabay_exp.set_enable_expansion(pixabay_cfg.get("enabled", True))

        def _toggle_pixabay(row, gparam):
            pixabay_cfg["enabled"] = row.get_enable_expansion()
            self.on_change()

        pixabay_exp.connect("notify::enable-expansion", _toggle_pixabay)

        pixabay_key_row = Adw.EntryRow()
        pixabay_key_row.set_title("API Key (Optional)")
        pixabay_key_row.set_text(pixabay_cfg.get("api_key", ""))

        def _change_pixabay_key(row):
            pixabay_cfg["api_key"] = row.get_text().strip()
            self.on_change()

        pixabay_key_row.connect("changed", _change_pixabay_key)
        pixabay_exp.add_row(pixabay_key_row)
        sources_group.add(pixabay_exp)

        # 4. Reddit Row
        reddit_cfg = sources_cfg.setdefault("reddit", {"enabled": True, "subreddits": []})
        reddit_exp = Adw.ExpanderRow()
        reddit_exp.set_title("Reddit")
        reddit_exp.set_subtitle("r/wallpapers, r/EarthPorn, r/spaceporn")
        reddit_exp.set_show_enable_switch(True)
        reddit_exp.set_enable_expansion(reddit_cfg.get("enabled", True))

        def _toggle_reddit(row, gparam):
            reddit_cfg["enabled"] = row.get_enable_expansion()
            self.on_change()

        reddit_exp.connect("notify::enable-expansion", _toggle_reddit)

        subs_row = Adw.EntryRow()
        subs_row.set_title("Subreddits (comma separated)")
        subs_row.set_text(", ".join(reddit_cfg.get("subreddits", ["wallpapers", "EarthPorn", "spaceporn"])))

        def _change_subs(row):
            items = [s.strip() for s in row.get_text().split(",") if s.strip()]
            reddit_cfg["subreddits"] = items
            self.on_change()

        subs_row.connect("changed", _change_subs)
        reddit_exp.add_row(subs_row)
        sources_group.add(reddit_exp)

        # 5. Local Folder Row
        local_cfg = sources_cfg.setdefault("local", {"enabled": False, "paths": ["~/Pictures/Wallpapers"]})
        local_exp = Adw.ExpanderRow()
        local_exp.set_title("Local Folder")
        local_exp.set_subtitle("Rotate images from your local directories")
        local_exp.set_show_enable_switch(True)
        local_exp.set_enable_expansion(local_cfg.get("enabled", False))

        def _toggle_local(row, gparam):
            local_cfg["enabled"] = row.get_enable_expansion()
            self.on_change()

        local_exp.connect("notify::enable-expansion", _toggle_local)

        paths_row = Adw.EntryRow()
        paths_row.set_title("Folder Paths (comma separated)")
        paths_row.set_text(", ".join(local_cfg.get("paths", ["~/Pictures/Wallpapers"])))

        def _change_paths(row):
            items = [p.strip() for p in row.get_text().split(",") if p.strip()]
            local_cfg["paths"] = items
            self.on_change()

        paths_row.connect("changed", _change_paths)
        local_exp.add_row(paths_row)
        sources_group.add(local_exp)

"""
GTK4 / Libadwaita settings GUI for awall.
"""

from __future__ import annotations


def is_gui_available() -> bool:
    """Checks if PyGObject and GTK4/Adwaita are available."""
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Gtk, Adw
        return True
    except Exception:
        return False

"""
GTK4 / Libadwaita Application entry point for awall.
"""

from __future__ import annotations

import sys
from awall.gui import is_gui_available


def launch_gui() -> int:
    """Launches the GTK4/Libadwaita graphical configuration window."""
    if not is_gui_available():
        print("[awall] GTK4 or Libadwaita is not installed.")
        print("Please install 'python-gobject', 'gtk4', and 'libadwaita' or use the CLI wizard with: awall config")
        return 1

    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gio, GLib
    from awall.gui.main_window import MainWindow

    class AwallApplication(Adw.Application):
        def __init__(self):
            super().__init__(
                application_id="io.github.awall.settings",
                flags=Gio.ApplicationFlags.FLAGS_NONE,
            )

        def do_activate(self):
            win = self.props.active_window
            if not win:
                win = MainWindow(self)
                win.set_icon_name("awall")
            win.present()

    app = AwallApplication()
    return app.run(None)

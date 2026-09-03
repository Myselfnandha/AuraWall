"""
GTK4 / Libadwaita Application entry point for awall.
"""

from __future__ import annotations

import sys
from awall.gui import is_gui_available


def is_tray_running() -> bool:
    """Checks if the awall tray process is currently active."""
    try:
        import os, subprocess
        my_pid = os.getpid()
        out = subprocess.check_output(["pgrep", "-f", "awall.*tray"]).decode("utf-8")
        pids = [int(p.strip()) for p in out.strip().split() if p.strip() and int(p.strip()) != my_pid]
        return len(pids) > 0
    except Exception:
        return False


def ensure_tray_running():
    """Spawns the awall tray process in the background if not already running."""
    if not is_tray_running():
        try:
            import os, subprocess, sys
            env = os.environ.copy()
            if "DISPLAY" not in env:
                env["DISPLAY"] = ":0.0"
            cmd = [sys.executable, "-m", "awall", "tray"]
            subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as e:
            print(f"[awall] Notice: Could not autostart tray ({e})")


def launch_gui(argv=None) -> int:
    """Launches the GTK4/Libadwaita graphical configuration window."""
    if not is_gui_available():
        print("[awall] GTK4 or Libadwaita is not installed.")
        print("Please install 'python-gobject', 'gtk4', and 'libadwaita' to launch the application.")
        return 1

    # Ensure background system tray is active
    ensure_tray_running()

    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gio
    from awall.gui.main_window import MainWindow

    class AwallApplication(Adw.Application):
        def __init__(self):
            super().__init__(
                application_id="io.github.awall.settings",
                flags=Gio.ApplicationFlags.NON_UNIQUE,
            )

        def do_activate(self):
            win = MainWindow(self)
            win.set_icon_name("awall")
            win.present()

    app = AwallApplication()
    args = [sys.argv[0]] if argv is None else [sys.argv[0]] + list(argv)
    return app.run(args)

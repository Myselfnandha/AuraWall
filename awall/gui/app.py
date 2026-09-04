"""
GTK4 / Libadwaita Application entry point for awall.
"""

from __future__ import annotations

import sys
from awall.gui import is_gui_available


def is_tray_running() -> bool:
    """Checks if the aurawall tray process is currently active."""
    try:
        import os, subprocess
        my_pid = os.getpid()
        out = subprocess.check_output(["pgrep", "-f", "tray"]).decode("utf-8")
        pids = [int(p.strip()) for p in out.strip().split() if p.strip() and int(p.strip()) != my_pid]
        return len(pids) > 0
    except Exception:
        return False


def ensure_tray_running():
    """Spawns the aurawall tray process in the background if not already running."""
    if not is_tray_running():
        try:
            import os, subprocess, sys, shutil
            env = os.environ.copy()
            if "DISPLAY" not in env:
                env["DISPLAY"] = ":0.0"
            tray_bin = shutil.which("aurawall") or shutil.which("awall")
            cmd = [tray_bin, "tray"] if tray_bin else [sys.executable, "-m", "awall", "tray"]
            subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as e:
            print(f"[aurawall] Notice: Could not autostart tray ({e})")


def launch_gui(argv=None) -> int:
    """Launches the GTK4/Libadwaita graphical configuration window."""
    if not is_gui_available():
        print("[aurawall] GTK4 or Libadwaita is not installed.")
        print("Please install 'python-gobject', 'gtk4', and 'libadwaita' to launch the application.")
        return 1

    # Ensure background system tray is active
    ensure_tray_running()

    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gio
    from awall.gui.main_window import MainWindow

    class AuraWallApplication(Adw.Application):
        def __init__(self):
            super().__init__(
                application_id="io.github.aurawall",
                flags=Gio.ApplicationFlags.NON_UNIQUE,
            )

        def do_activate(self):
            win = MainWindow(self)
            win.set_icon_name("aurawall")
            win.present()

    app = AuraWallApplication()
    args = [sys.argv[0]] if argv is None else [sys.argv[0]] + list(argv)
    return app.run(args)

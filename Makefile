.PHONY: all install install-user uninstall uninstall-user test run

all: install-user

install-user:
	@bash ./install.sh

install:
	@pip install .
	@install -Dm644 desktop/io.github.awall.desktop /usr/share/applications/io.github.awall.desktop
	@ln -sf io.github.awall.desktop /usr/share/applications/awall.desktop
	@install -Dm644 awall/assets/icon-32.png /usr/share/icons/hicolor/32x32/apps/awall.png
	@install -Dm644 awall/assets/icon-64.png /usr/share/icons/hicolor/64x64/apps/awall.png
	@install -Dm644 awall/assets/icon-128.png /usr/share/icons/hicolor/128x128/apps/awall.png
	@install -Dm644 awall/assets/icon.png /usr/share/icons/hicolor/256x256/apps/awall.png
	@install -Dm644 awall/assets/icon.png /usr/share/pixmaps/awall.png
	@install -Dm644 systemd/awall.service /usr/lib/systemd/user/awall.service
	@install -Dm644 systemd/awall.timer /usr/lib/systemd/user/awall.timer
	@which update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/share/applications || true
	@which gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true

uninstall-user:
	@python3 -c "from awall.desktop import uninstall_desktop_app; uninstall_desktop_app()"
	@python3 -c "from awall.autostart import disable_autostart; disable_autostart()"
	@python3 -c "from awall.service import ServiceManager; ServiceManager().uninstall()"
	@pip uninstall -y awall || true

uninstall: uninstall-user
	@rm -f /usr/share/applications/io.github.awall.desktop /usr/share/applications/awall.desktop
	@rm -f /usr/share/icons/hicolor/*/apps/awall.png /usr/share/pixmaps/awall.png
	@rm -f /usr/lib/systemd/user/awall.service /usr/lib/systemd/user/awall.timer

test:
	@python3 -m unittest discover tests

run:
	@python3 -m awall

# Maintainer: awall contributors <awall@example.com>
pkgname=awall
pkgver=0.1.0
pkgrel=1
pkgdesc="Free Automatic Wallpaper Engine for Arch Linux with multi-source fallback, transitions & GTK4 GUI"
arch=('any')
url="https://github.com/user/awall"
license=('MIT')
depends=('python' 'python-yaml' 'python-requests' 'python-pillow' 'python-gobject' 'gtk4' 'libadwaita')
optdepends=(
    'libappindicator-gtk3: for desktop system tray icon'
    'libnotify: for desktop notifications'
    'feh: for standalone X11 wallpaper setting'
    'swaybg: for Sway / wlroots wallpaper setting'
    'hyprpaper: for Hyprland wallpaper setting'
    'swww: for animated Wayland transitions'
    'nitrogen: for X11 wallpaper management'
)
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$srcdir/$pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$srcdir/$pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    
    # Desktop Application Launcher & Shortcuts
    install -Dm644 desktop/io.github.awall.desktop "$pkgdir/usr/share/applications/io.github.awall.desktop"
    ln -sf io.github.awall.desktop "$pkgdir/usr/share/applications/awall.desktop"
    
    # Application Icons
    install -Dm644 awall/assets/icon-32.png "$pkgdir/usr/share/icons/hicolor/32x32/apps/awall.png"
    install -Dm644 awall/assets/icon-64.png "$pkgdir/usr/share/icons/hicolor/64x64/apps/awall.png"
    install -Dm644 awall/assets/icon-128.png "$pkgdir/usr/share/icons/hicolor/128x128/apps/awall.png"
    install -Dm644 awall/assets/icon.png "$pkgdir/usr/share/icons/hicolor/256x256/apps/awall.png"
    install -Dm644 awall/assets/icon.png "$pkgdir/usr/share/pixmaps/awall.png"

    # systemd User Service & Timer for startup / background rotation
    install -Dm644 systemd/awall.service "$pkgdir/usr/lib/systemd/user/awall.service"
    install -Dm644 systemd/awall.timer "$pkgdir/usr/lib/systemd/user/awall.timer"
}

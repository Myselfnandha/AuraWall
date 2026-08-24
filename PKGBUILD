# Maintainer: awall contributors <awall@example.com>
pkgname=awall
pkgver=0.1.0
pkgrel=1
pkgdesc="Free Automatic Wallpaper Engine for Arch Linux with multi-source fallback, transitions & GTK4 GUI"
arch=('any')
url="https://github.com/user/awall"
license=('MIT')
depends=('python' 'python-yaml' 'python-requests' 'python-pillow')
optdepends=(
    'python-gobject: for GTK4 settings GUI'
    'gtk4: for GTK4 settings GUI'
    'libadwaita: for modern Adwaita styling'
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
    install -Dm644 systemd/awall.service "$pkgdir/usr/lib/systemd/user/awall.service"
    install -Dm644 systemd/awall.timer "$pkgdir/usr/lib/systemd/user/awall.timer"
}

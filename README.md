# 🌌 AuraWall — Next-Generation Linux Wallpaper Engine

<div align="center">

![Linux](https://img.shields.io/badge/Platform-Linux-FCC624?logo=linux&logoColor=black)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![GTK4](https://img.shields.io/badge/UI-GTK4%20%2F%20Libadwaita-4A90E2?logo=gnome&logoColor=white)
![Arch Linux](https://img.shields.io/badge/Arch-Linux-1793D1?logo=arch-linux&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

**Free, smart, and dynamic desktop ambiance daemon with live countdown badges, weather-reactive art, and multi-monitor curation.**

[Features](#-key-features) • [Installation](#-installation) • [CLI Usage](#-cli-cheatsheet) • [Desktop Environments](#-supported-desktops) • [Contributing](#-contributing)

</div>

---

## ✨ Key Features

- ⏱ **Live Digital Countdown Badge**: Pixel-perfect 24x24 square panel tray icon rendering real-time minutes & seconds (`04:32`, `04:31`...) with zero horizontal distortion.
- ⚡ **Smart Power-Saving Window Pause**: Zero wakeups while gaming or working in applications. Automatically pauses countdown during active window/fullscreen use and resumes seamlessly when returning to the desktop.
- ☀️ **Solar Sun & Real-Time Weather Engine**: macOS-style dynamic lighting computed from physical solar coordinates (Dawn, Sunrise, Solar Noon, Golden Hour, Sunset, Twilight, Night) combined with real-time weather conditions via Open-Meteo.
- 🌐 **4K Ultra-HD Multi-Source Pipeline**:
  - **Bing Wallpaper**: Curated daily UHD 4K photographic archive
  - **Wallhaven**: Community 4K digital art, anime, and minimal illustrations
  - **Unsplash**: High-resolution photography with aspect ratio preservation
  - **Pexels & Pixabay**: Royalty-free artistic collections
  - **Reddit**: Direct feeds from `r/wallpapers`, `r/EarthPorn`, `r/spaceporn`
  - **Local Directory**: Personal offline wallpaper libraries
- 🖥 **True Multi-Monitor Support**: Configure independent wallpapers per display (`eDP-1`, `HDMI-1`, `DP-1`) or unified desktop spanning.
- 🔒 **Lock Screen Wallpaper Synchronization**: Automatically syncs desktop art to lock screen (`xfce4-screensaver`, `lightdm`, `gnome-screensaver`, `kscreenlocker`, `swaylock`, `hyprlock`, `betterlockscreen`) with optional Gaussian Blur and Dim overlays.
- 🎨 **GTK4 / Libadwaita Preferences & Library**: Full visual desktop manager with cache search, thumbnail grid, 1-click apply, and granular source filters.
- 🔄 **Intelligent Instant Fallback Chain**: Pre-fetched zero-delay wallpaper rotations with automatic offline fallback when disconnected from the internet.
- 🚀 **Zero-Config Systemd Automation**: Background user service & timer (`aurawall.timer`) with seamless login autostart.

---

## 🚀 Installation

### One-Step Complete Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/Myselfnandha/AuraWall.git
cd AuraWall

# Install package, desktop launcher (.desktop), tray autostart & systemd timer
./install.sh
```

### Manual Installation via Pip

```bash
pip install --user .
# Or in editable mode for development:
pip install -e .
```

---

## ⌨️ CLI Cheatsheet

Both `aurawall` and `awall` can be used interchangeably:

| Command | Description |
| :--- | :--- |
| `aurawall` / `aurawall gui` | Launch the GTK4 / Libadwaita settings application & gallery |
| `aurawall next` | Rotate immediately to the next wallpaper |
| `aurawall prev` | Revert to the previous wallpaper in history |
| `aurawall fav` | Mark the current wallpaper as a favorite |
| `aurawall pause` | Toggle master rotation pause |
| `aurawall resume` | Resume automatic rotation |
| `aurawall tray` | Run the system tray icon with live countdown badge |
| `aurawall lockscreen sync` | Manually sync current wallpaper to system lock screen |
| `aurawall monitors` | Inspect connected display monitors and assigned modes |
| `aurawall status` | View active source, remaining timer, and systemd service state |
| `aurawall autostart enable` | Enable automatic tray daemon launch on desktop login |

---

## 🖥 Supported Desktops

AuraWall auto-detects your graphical session and connects directly to the native backend:

- **XFCE / Xubuntu** (`xfce4-desktop`, `xfconf-query`)
- **GNOME** (`gsettings` light & dark picture-uri)
- **KDE Plasma 5 & 6** (DBus scripting & `kscreenlockerrc`)
- **Hyprland** (`hyprpaper`, `swww`)
- **Sway / Wayland** (`swaybg`)
- **i3 / bspwm / Awesome / X11** (`feh`, `nitrogen`, `xwallpaper`)

---

## ⚙️ Configuration

Configuration is stored in standard XDG format at `~/.config/aurawall/config.yaml`:

```yaml
version: 1
paused: false
active_source: "auto"

sources:
  fallback_order:
    - wallhaven
    - bing
    - unsplash
    - pexels
    - pixabay
    - reddit
    - local

schedule:
  interval_minutes: 5
  pause_on_active_window: true
  on_boot: true

display:
  scaling: "fill"
  multi_monitor: "unified"
  lock_screen:
    enabled: true
    effect: "blur_dim"
    blur_radius: 15
    dim_opacity: 0.4
```

---

## 🗑 Uninstallation

To completely remove AuraWall, including all systemd units, autostart entries, and icons:

```bash
./uninstall.sh
```

---

## 📜 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

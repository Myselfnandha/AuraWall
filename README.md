# 🖼 awall — Free Automatic Wallpaper Engine

> A modern, lightweight, and versatile automatic wallpaper engine for Arch Linux & beyond. Pulls high-resolution photography and digital art from **Unsplash**, **Pexels**, **Pixabay**, **Reddit**, and local directories with smooth transitions, smart offline caching, and desktop integration.

---

## ✨ Features

- 🌐 **Multi-Source Support**: Fetches from Unsplash, Pexels, Pixabay, Reddit (e.g. `r/wallpapers`, `r/EarthPorn`, `r/spaceporn`), and local folders.
- ☀️ **Dynamic Solar & Weather Engine**: macOS-style dynamic lighting! Computes sun elevation (Dawn, Sunrise, Noon, Golden Hour, Sunset, Night) and syncs live weather with Open-Meteo.
- 🖥 **Multi-Monitor Per-Display Support**: Display separate unique wallpapers on each connected monitor (eDP-1, HDMI-1, etc.) or mirror primary display.
- 🔒 **Lock Screen Wallpaper Sync**: Automatically syncs desktop wallpaper to lock screen (XFCE, GNOME, KDE, i3lock, betterlockscreen, swaylock, hyprlock) with optional Gaussian Blur and Dim overlays.
- 🗔 **System Tray Integration**: Full desktop tray icon (`awall tray`) with quick source/category switching, next/prev, and favorites.
- ⚡ **Smart Power-Saving Focus Pause**: System-event triggered (0% CPU / 0 wakeups while working in apps). Automatically pauses rotation during application use and changes wallpaper immediately when returning to desktop if overdue.
- 🚀 **Desktop Autostart**: Easy XDG login autostart for system tray & engine (`awall autostart enable`).
- 🔄 **Intelligent Fallback Chain**: Never fails to set a wallpaper — automatically falls back to secondary sources or cached images.
- 🏷 **17 Curated Categories**: Nature, Architecture, Animals, Space, Technology, Dark Aesthetic, Minimalist, 3D Renders, Street Photography, and more.
- 🎨 **Visual Transitions**: Smooth crossfade blending, horizontal sliding, or instant wallpaper swaps.
- 🖥 **Universal Desktop Support**: Auto-detects XFCE, GNOME, KDE Plasma, Hyprland, Sway, feh, nitrogen, swww, and xwallpaper.
- ⚙️ **GTK4 / Libadwaita Preferences**: Modern settings GUI (`awall gui`) for configuring schedules, multi-monitor, lockscreen, sources, and dynamic presets.
- ★ **Favorites System**: Save wallpapers you love (`awall fav`) — favorites are protected from cache cleanup and prioritized offline.
- 📡 **Offline Mode**: Automatically falls back to high-resolution cached wallpapers when disconnected from the internet.
- ⏱ **Background Automation**: Native `systemd` user timer for reliable, zero-overhead background rotation.
- 🔔 **Desktop Notifications**: Displays photographer credit and link via `notify-send` when wallpapers change.

---

## 🚀 Quick One-Step Installation

```bash
# Clone the repository
git clone https://github.com/user/auto_wall.git
cd auto_wall

# One-step complete install (App launcher + Icons + Tray Autostart + systemd timer)
./install.sh
```

### Or using AUR (Arch User Repository)
```bash
cd auto_wall
makepkg -si
```

---

## ⚡ Features & Usage

### 1. Launch Settings & Preferences Application
Open **"awall Wallpaper Engine"** directly from your desktop Application Menu / App Grid, or run:
```bash
awall
```

### 2. Desktop System Tray Icon
```bash
awall tray
```
Right-click or click the system tray icon to switch sources, jump to the next/previous wallpaper, pause rotation, or access preferences.

### 3. Startup Autorun
Startup autorun is supported via two integrated methods:
- **Desktop Login Autostart (XDG Autostart)**: Automatically launches the tray icon on desktop login:
  ```bash
  awall autostart enable
  ```
- **Background Systemd Timer**: Automatically rotates wallpapers on boot and on schedule without requiring the GUI:
  ```bash
  awall service install
  ```

### 4. Application Menu Integration
Install or refresh desktop application shortcuts (`.desktop`) and icons in `~/.local/share/applications/`:
```bash
awall app install
```

---

## ⌨️ Command Reference

| Action | Command |
|---|---|
| Launch Settings GUI | `awall` or `awall gui` |
| Launch Desktop System Tray | `awall tray` |
| Rotate to Next Wallpaper | `awall next` |
| Revert to Previous Wallpaper | `awall prev` |
| Manage Lock Screen Wallpaper Sync | `awall lockscreen [sync\|status]` |
| Inspect Connected Displays & Multi-Monitor | `awall monitors` |
| Manage Desktop Startup Autostart | `awall autostart [enable\|disable\|status]` |
| Manage Desktop App Menu & Icons | `awall app [install\|uninstall\|status]` |
| Manage Background systemd Timer | `awall service [install\|uninstall\|status]` |
| Favorite / Unfavorite Wallpaper | `awall fav` / `awall unfav` / `awall favorites` |
| Check Solar Position & Weather | `awall weather` |
| Pause / Resume Rotation | `awall pause` / `awall resume` |
| Engine Status & Info | `awall status` / `awall info` / `awall history` |

---

## 📁 Configuration (`~/.config/auto_wall/config.yaml`)

```yaml
version: 1
paused: false
active_source: auto

display:
  scaling: fill  # fill, fit, stretch, center, tile
  multi_monitor: per_monitor  # "unified" or "per_monitor"
  monitor_config:
    eDP-1:
      mode: unique  # "unique" or "shared"
    HDMI-1:
      mode: unique
  transition: fade  # fade, slide, instant
  transition_duration_ms: 500
  lock_screen:
    enabled: true
    effect: blur  # "none", "blur", "dim", "blur_dim"
    blur_radius: 15
    dim_opacity: 0.4

sources:
  fallback_order:
    - unsplash
    - pexels
    - pixabay
    - reddit
    - local
  unsplash:
    enabled: true
    api_key: ""
  pexels:
    enabled: true
    api_key: ""
  pixabay:
    enabled: true
    api_key: ""
  reddit:
    enabled: true
    subreddits:
      - wallpapers
      - EarthPorn
      - spaceporn
  local:
    enabled: false
    paths:
      - ~/Pictures/Wallpapers

topics:
  enabled:
    - wallpapers
    - nature
    - architecture
    - space
    - technology
    - dark_moody
    - minimalist
  mode: mixed  # "mixed" or "sequential"

schedule:
  interval_minutes: 5
  on_boot: true

display:
  scaling: fill  # fill, fit, stretch, center, tile
  transition: fade  # fade, slide, instant
  transition_duration_ms: 500

cache:
  directory: ~/.cache/auto_wall
  max_wallpapers: 50

notifications:
  enabled: true
  show_credits: true

wallpaper_backend: auto
```

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

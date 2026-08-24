# 🖼 awall — Free Automatic Wallpaper Engine

> A modern, lightweight, and versatile automatic wallpaper engine for Arch Linux & beyond. Pulls high-resolution photography and digital art from **Unsplash**, **Pexels**, **Pixabay**, **Reddit**, and local directories with smooth transitions, smart offline caching, and desktop integration.

---

## ✨ Features

- 🌐 **Multi-Source Support**: Fetches from Unsplash, Pexels, Pixabay, Reddit (e.g. `r/wallpapers`, `r/EarthPorn`, `r/spaceporn`), and local folders.
- ☀️ **Dynamic Solar & Weather Engine**: macOS-style dynamic lighting! Computes sun elevation (Dawn, Sunrise, Noon, Golden Hour, Sunset, Night) and syncs live weather with Open-Meteo.
- 🕒 **Desktop Overlay Widgets**: Composites high-contrast Digital Clock, Date, Live Weather Badge, Media Player track, and Daily Quotes onto wallpapers.
- 🗔 **System Tray Integration**: Full desktop tray icon (`awall tray`) with quick source/category switching, next/prev, and favorites.
- 🚀 **Desktop Autostart**: Easy XDG login autostart for system tray & engine (`awall autostart enable`).
- 🔄 **Intelligent Fallback Chain**: Never fails to set a wallpaper — automatically falls back to secondary sources or cached images.
- 🏷 **17 Curated Categories**: Nature, Architecture, Animals, Space, Technology, Dark Aesthetic, Minimalist, 3D Renders, Street Photography, and more.
- 🎨 **Visual Transitions**: Smooth crossfade blending, horizontal sliding, or instant wallpaper swaps.
- 🖥 **Universal Desktop Support**: Auto-detects XFCE, GNOME, KDE Plasma, Hyprland, Sway, feh, nitrogen, swww, and xwallpaper.
- ⚙️ **Dual Interface**: Fast interactive terminal wizard (`awall config`) and modern GTK4/Libadwaita settings GUI (`awall gui`).
- ★ **Favorites System**: Save wallpapers you love (`awall fav`) — favorites are protected from cache cleanup and prioritized offline.
- 📡 **Offline Mode**: Automatically falls back to high-resolution cached wallpapers when disconnected from the internet.
- ⏱ **Background Automation**: Native `systemd` user timer for reliable, zero-overhead background rotation.
- 🔔 **Desktop Notifications**: Displays photographer credit and link via `notify-send` when wallpapers change.

---

## 🚀 Installation on Arch Linux

### Method 1: Local / Pipx Install
```bash
# Clone the repository
git clone https://github.com/user/auto_wall.git
cd auto_wall

# Install in editable mode or user mode
pip install --user .

# Or using pipx
pipx install .
```

### Method 2: AUR (Arch User Repository)
```bash
cd auto_wall
makepkg -si
```

---

## ⚡ Quick Start

### 1. Run First-Time Setup Wizard
```bash
awall config
```

### 2. Launch System Tray Icon
```bash
awall tray
```

### 3. Launch Graphical Settings Panel (Optional)
```bash
awall gui
# or
awall config --gui
```

### 4. Rotate to Next Wallpaper Now
```bash
awall next
```

### 5. Check Solar Position & Live Weather
```bash
awall weather
```

### 6. Enable Desktop Overlay Widgets (Clock, Weather, Quotes)
```bash
awall widgets enable
```

---

## ⌨️ CLI Command Reference

| Command | Description |
|---|---|
| `awall tray` | Launch desktop system tray icon with quick actions |
| `awall next` | Immediately download and set the next wallpaper |
| `awall prev` | Revert to previous wallpaper in history |
| `awall weather` | Display current solar position, elevation, and live weather |
| `awall widgets [enable\|disable\|status]` | Toggle desktop clock, weather, and quote widgets |
| `awall autostart [enable\|disable\|status]` | Manage desktop login autostart for tray icon |
| `awall fav` | Mark current wallpaper as favorite (protected from cache cleanup) |
| `awall unfav` | Remove favorite status from current wallpaper |
| `awall favorites` | List all saved favorite wallpapers |
| `awall status` | Show current wallpaper, source, timer status, and cache stats |
| `awall info` | Display detailed photographer credits, resolution, and URL |
| `awall history` | Show recent history log of applied wallpapers |
| `awall pause` / `awall resume` | Pause or resume background wallpaper rotation |
| `awall set-source <name>` | Quickly switch active source (`unsplash`, `pexels`, `pixabay`, `reddit`, `local`, `auto`) |
| `awall config` | Run interactive terminal setup wizard |
| `awall gui` | Open modern GTK4 / Libadwaita settings window |
| `awall service install` | Install and start background `systemd` user timer |
| `awall service uninstall` | Stop and remove background `systemd` timer |
| `awall service status` | Check status of systemd timer |

---

## 📁 Configuration (`~/.config/auto_wall/config.yaml`)

```yaml
version: 1
paused: false
active_source: auto

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

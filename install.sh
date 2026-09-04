#!/usr/bin/env bash
# ==============================================================================
# AuraWall - Next-generation Wallpaper Engine Installation Script
# Installs application, desktop launcher, icons, systemd timer, and login autostart
# ==============================================================================

set -e

BOLD="\033[1m"
GREEN="\033[92m"
BLUE="\033[94m"
CYAN="\033[96m"
YELLOW="\033[93m"
RESET="\033[0m"

echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║  🌌 Installing AuraWall Wallpaper Engine Desktop Application ║${RESET}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}\n"

# 1. Install python package
echo -e "${BLUE}▶ Installing AuraWall package to user environment...${RESET}"
if pip install --user . --no-warn-script-location 2>/dev/null; then
    echo -e "${GREEN}✓ Package installed successfully.${RESET}"
elif pip install --user . --break-system-packages --no-warn-script-location; then
    echo -e "${GREEN}✓ Package installed successfully with pip.${RESET}"
elif command -v pipx >/dev/null 2>&1; then
    pipx install . --force
    echo -e "${GREEN}✓ Package installed successfully with pipx.${RESET}"
else
    echo -e "${YELLOW}Warning: Could not run pip. Running in local source mode.${RESET}"
fi

# Ensure ~/.local/bin is in PATH for this session
export PATH="$HOME/.local/bin:$PATH"

# 2. Install desktop application launcher & icons
echo -e "${BLUE}▶ Installing Desktop Launcher (.desktop) & High-Resolution Icons...${RESET}"
python3 -c "from awall.desktop import install_desktop_app; install_desktop_app()"

# 3. Enable desktop login autostart
echo -e "${BLUE}▶ Enabling Desktop Login Autostart (XDG Autostart)...${RESET}"
python3 -c "from awall.autostart import enable_autostart; enable_autostart()"

# 4. Install and enable systemd user service & timer
echo -e "${BLUE}▶ Installing and activating background systemd timer...${RESET}"
python3 -c "from awall.service import ServiceManager; ServiceManager().install(interval_minutes=5, on_boot=True)"

echo -e "\n${GREEN}${BOLD}✓ Installation Complete! 🎉${RESET}"
echo -e "  • ${BOLD}Application Launcher:${RESET} Available in your desktop application menu / App Grid (AuraWall)"
echo -e "  • ${BOLD}Startup Autorun:${RESET} Enabled automatically on login and boot"
echo -e "  • ${BOLD}Launch Commands:${RESET} Run '${CYAN}aurawall${RESET}' or '${CYAN}awall${RESET}' to open GUI / CLI\n"

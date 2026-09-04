#!/usr/bin/env bash
# ==============================================================================
# AuraWall - Complete Uninstallation Script
# ==============================================================================

set -e

BOLD="\033[1m"
GREEN="\033[92m"
BLUE="\033[94m"
RED="\033[91m"
RESET="\033[0m"

echo -e "${RED}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${RED}${BOLD}║  🗑  Uninstalling AuraWall Wallpaper Engine                  ║${RESET}"
echo -e "${RED}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}\n"

# 1. Stop and disable systemd service & timer
echo -e "${BLUE}▶ Removing background systemd units...${RESET}"
python3 -c "from awall.service import ServiceManager; ServiceManager().uninstall()" 2>/dev/null || true

# 2. Disable login autostart
echo -e "${BLUE}▶ Removing desktop login autostart...${RESET}"
python3 -c "from awall.autostart import disable_autostart; disable_autostart()" 2>/dev/null || true

# 3. Remove .desktop application entries
echo -e "${BLUE}▶ Removing desktop application launcher and icons...${RESET}"
python3 -c "from awall.desktop import uninstall_desktop_app; uninstall_desktop_app()" 2>/dev/null || true

# 4. Uninstall python packages
echo -e "${BLUE}▶ Removing python packages...${RESET}"
pip uninstall -y aurawall awall 2>/dev/null || true

echo -e "\n${GREEN}${BOLD}✓ AuraWall has been completely uninstalled.${RESET}\n"

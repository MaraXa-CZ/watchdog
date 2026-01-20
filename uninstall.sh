#!/bin/bash
#
# Watchdog v1.0 - Uninstaller
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="/opt/watchdog"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Watchdog Uninstaller                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Run as root: sudo bash uninstall.sh${NC}"
    exit 1
fi

echo -e "${YELLOW}This will completely remove Watchdog!${NC}"
echo ""
read -p "Are you sure? (y/N): " CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "[*] Stopping services..."
systemctl stop watchdog watchdog-web 2>/dev/null || true
systemctl disable watchdog watchdog-web 2>/dev/null || true

echo "[*] Removing service files..."
rm -f /etc/systemd/system/watchdog.service
rm -f /etc/systemd/system/watchdog-web.service
systemctl daemon-reload

echo "[*] Removing installation directory..."
rm -rf "$INSTALL_DIR"

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}              UNINSTALL COMPLETE${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""

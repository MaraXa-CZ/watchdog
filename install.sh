#!/bin/bash
#
# Watchdog v1.0 - Installer
# ==========================
# Universal installer for Raspberry Pi
#
# Supports:
# - Raspberry Pi OS: Bullseye (11), Bookworm (12), Trixie (13+)
# - Ubuntu: 22.04, 24.04
# - Raspberry Pi: 1, 2, 3, 4, 5, Zero, Zero 2 W
#
# Usage: sudo bash install.sh
#

set -e

VERSION="1.0"
INSTALL_DIR="/opt/watchdog"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_step() { echo -e "${CYAN}[*]${NC} $1"; }
print_ok() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

# ============================================================================
# System Detection
# ============================================================================

detect_system() {
    # Detect OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_NAME="$ID"
        OS_CODENAME="$VERSION_CODENAME"
    else
        OS_NAME="unknown"
        OS_CODENAME="unknown"
    fi
    
    # Map codename to version
    case "$OS_CODENAME" in
        "buster")    OS_MAJOR=10 ;;
        "bullseye")  OS_MAJOR=11 ;;
        "bookworm")  OS_MAJOR=12 ;;
        "trixie")    OS_MAJOR=13 ;;
        "forky")     OS_MAJOR=14 ;;
        "jammy")     OS_MAJOR=12 ;;  # Ubuntu 22.04
        "noble")     OS_MAJOR=13 ;;  # Ubuntu 24.04
        *)           OS_MAJOR=12 ;;
    esac
    
    # Detect Pi model
    PI_MODEL="unknown"
    PI_VERSION=0
    if [ -f /proc/device-tree/model ]; then
        PI_MODEL_STRING=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null)
        case "$PI_MODEL_STRING" in
            *"Pi 5"*)      PI_MODEL="Pi 5"; PI_VERSION=5 ;;
            *"Pi 4"*)      PI_MODEL="Pi 4"; PI_VERSION=4 ;;
            *"Pi 3"*)      PI_MODEL="Pi 3"; PI_VERSION=3 ;;
            *"Pi 2"*)      PI_MODEL="Pi 2"; PI_VERSION=2 ;;
            *"Pi Zero 2"*) PI_MODEL="Pi Zero 2"; PI_VERSION=3 ;;
            *"Pi Zero"*)   PI_MODEL="Pi Zero"; PI_VERSION=1 ;;
            *"Pi Model"*)  PI_MODEL="Pi 1"; PI_VERSION=1 ;;
        esac
    fi
    
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              Watchdog v${VERSION} Installer                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  OS: $OS_NAME $OS_CODENAME (Debian $OS_MAJOR)"
    echo "  Pi: $PI_MODEL"
    echo ""
}

# ============================================================================
# Check for existing installation
# ============================================================================

check_existing() {
    UPDATE_MODE=false
    
    # Check for USER DATA (not git files) to detect real installation
    if [ -f "$INSTALL_DIR/config.json" ] || [ -f "$INSTALL_DIR/users.json" ]; then
        UPDATE_MODE=true
        print_warn "Existing installation detected - will preserve config"
    fi
}

# ============================================================================
# Install dependencies
# ============================================================================

install_dependencies() {
    print_step "Installing dependencies..."
    
    apt-get update -qq
    
    # Base packages
    apt-get install -y -qq \
        python3 \
        python3-flask \
        python3-werkzeug \
        git \
        curl \
        > /dev/null 2>&1
    
    # GPIO libraries based on OS and Pi
    print_step "Installing GPIO libraries..."
    
    if [ "$OS_MAJOR" -ge 13 ]; then
        # Trixie+: gpiod
        apt-get install -y -qq python3-libgpiod gpiod > /dev/null 2>&1 || true
        [ "$PI_VERSION" -ge 5 ] && apt-get install -y -qq python3-lgpio > /dev/null 2>&1 || true
    elif [ "$PI_VERSION" -ge 5 ]; then
        # Pi 5 on Bookworm: lgpio
        apt-get install -y -qq python3-lgpio > /dev/null 2>&1 || true
    else
        # Legacy: RPi.GPIO
        apt-get install -y -qq python3-rpi.gpio python3-gpiozero > /dev/null 2>&1 || true
    fi
    
    print_ok "Dependencies installed"
}

# ============================================================================
# Install files
# ============================================================================

install_files() {
    print_step "Installing files..."
    
    # Create directories
    mkdir -p "$INSTALL_DIR"/{log,stats,backups,commands}
    
    # Backup user data if exists
    [ -f "$INSTALL_DIR/config.json" ] && cp "$INSTALL_DIR/config.json" /tmp/watchdog_config.json.bak
    [ -f "$INSTALL_DIR/users.json" ] && cp "$INSTALL_DIR/users.json" /tmp/watchdog_users.json.bak
    
    # Copy files (if running from different directory)
    if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
        cp "$SCRIPT_DIR"/*.py "$INSTALL_DIR/" 2>/dev/null || true
        cp "$SCRIPT_DIR"/*.sh "$INSTALL_DIR/" 2>/dev/null || true
        cp "$SCRIPT_DIR"/*.txt "$INSTALL_DIR/" 2>/dev/null || true
        cp "$SCRIPT_DIR"/*.md "$INSTALL_DIR/" 2>/dev/null || true
        cp -r "$SCRIPT_DIR/templates" "$INSTALL_DIR/" 2>/dev/null || true
        cp -r "$SCRIPT_DIR/mobile" "$INSTALL_DIR/" 2>/dev/null || true
    fi
    
    # Restore user data
    [ -f /tmp/watchdog_config.json.bak ] && cp /tmp/watchdog_config.json.bak "$INSTALL_DIR/config.json"
    [ -f /tmp/watchdog_users.json.bak ] && cp /tmp/watchdog_users.json.bak "$INSTALL_DIR/users.json"
    
    # Set permissions
    chmod +x "$INSTALL_DIR"/*.sh 2>/dev/null || true
    chmod 777 "$INSTALL_DIR"/{log,stats,backups,commands}
    
    # Git safe directory
    git config --global --add safe.directory "$INSTALL_DIR" 2>/dev/null || true
    
    print_ok "Files installed"
}

# ============================================================================
# Network configuration (fresh install only)
# ============================================================================

configure_network() {
    [ "$UPDATE_MODE" = true ] && return
    
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                   Network Configuration                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    CURRENT_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    CURRENT_GW=$(ip route | grep default | awk '{print $3}' | head -1)
    IFACE=$(ip route | grep default | awk '{print $5}' | head -1)
    IFACE=${IFACE:-eth0}
    
    echo "  Interface: $IFACE"
    echo "  Current IP: $CURRENT_IP"
    echo "  Gateway: $CURRENT_GW"
    echo ""
    
    read -p "Configure static IP? (y/N): " CONFIGURE_NETWORK
    
    if [[ "$CONFIGURE_NETWORK" =~ ^[Yy]$ ]]; then
        read -p "Static IP [$CURRENT_IP]: " STATIC_IP
        STATIC_IP=${STATIC_IP:-$CURRENT_IP}
        
        read -p "Netmask [255.255.255.0]: " NETMASK
        NETMASK=${NETMASK:-255.255.255.0}
        
        read -p "Gateway [$CURRENT_GW]: " GATEWAY
        GATEWAY=${GATEWAY:-$CURRENT_GW}
        
        read -p "DNS [8.8.8.8 1.1.1.1]: " DNS
        DNS=${DNS:-"8.8.8.8 1.1.1.1"}
        
        echo ""
        read -p "Apply? (y/N): " APPLY
        
        if [[ "$APPLY" =~ ^[Yy]$ ]]; then
            # Calculate CIDR
            IFS='.' read -r i1 i2 i3 i4 <<< "$NETMASK"
            CIDR=$(echo "obase=2;$i1;$i2;$i3;$i4" | bc 2>/dev/null | tr -d '\n' | grep -o '1' | wc -l)
            CIDR=${CIDR:-24}
            
            # Detect network manager type and configure
            if systemctl is-active NetworkManager > /dev/null 2>&1; then
                # NetworkManager
                nmcli connection delete "watchdog-$IFACE" 2>/dev/null || true
                nmcli connection add type ethernet con-name "watchdog-$IFACE" ifname "$IFACE" \
                    ipv4.method manual ipv4.addresses "$STATIC_IP/$CIDR" \
                    ipv4.gateway "$GATEWAY" ipv4.dns "${DNS// /,}" \
                    connection.autoconnect yes > /dev/null
                print_ok "NetworkManager configured"
                NETWORK_CONFIGURED=true
                
            elif [ -f /etc/dhcpcd.conf ]; then
                # dhcpcd
                cp /etc/dhcpcd.conf /etc/dhcpcd.conf.backup
                sed -i '/# Watchdog static/,$d' /etc/dhcpcd.conf
                cat >> /etc/dhcpcd.conf << EOF

# Watchdog static configuration
interface $IFACE
static ip_address=$STATIC_IP/$CIDR
static routers=$GATEWAY
static domain_name_servers=$DNS
EOF
                print_ok "dhcpcd configured"
                NETWORK_CONFIGURED=true
            fi
        fi
    fi
}

# ============================================================================
# Create default config
# ============================================================================

create_config() {
    [ -f "$INSTALL_DIR/config.json" ] && return
    
    print_step "Creating default config..."
    
    cat > "$INSTALL_DIR/config.json" << 'EOF'
{
  "version": "1.0",
  "check_interval": 10,
  "outlets": {
    "outlet_1": {"name": "Outlet 1", "gpio_pin": 17, "active_high": true},
    "outlet_2": {"name": "Outlet 2", "gpio_pin": 18, "active_high": true},
    "outlet_3": {"name": "Outlet 3", "gpio_pin": 27, "active_high": true},
    "outlet_4": {"name": "Outlet 4", "gpio_pin": 22, "active_high": true}
  },
  "groups": [],
  "smtp": {"enabled": false},
  "system": {"debug": false, "stats_enabled": true, "timezone": "Europe/Prague", "language": "cs"},
  "web": {"port": 80}
}
EOF
    print_ok "Config created"
}

# ============================================================================
# Create admin user
# ============================================================================

create_admin() {
    [ -f "$INSTALL_DIR/users.json" ] && return
    
    print_step "Creating admin user..."
    
    echo ""
    read -p "Admin password [admin]: " ADMIN_PASS
    ADMIN_PASS=${ADMIN_PASS:-admin}
    
    python3 << PYEOF
import json
from werkzeug.security import generate_password_hash
from datetime import datetime

password = """$ADMIN_PASS"""
users = {
    "users": {
        "admin": {
            "password_hash": generate_password_hash(password),
            "role": "admin",
            "language": "cs",
            "theme": "dark",
            "created": datetime.now().isoformat()
        }
    }
}

with open("$INSTALL_DIR/users.json", "w") as f:
    json.dump(users, f, indent=2)
PYEOF
    
    print_ok "Admin user created"
}

# ============================================================================
# Setup systemd services
# ============================================================================

setup_services() {
    print_step "Setting up services..."
    
    # Watchdog daemon
    cat > /etc/systemd/system/watchdog.service << EOF
[Unit]
Description=Watchdog Monitor
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/watchdog.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Web interface
    cat > /etc/systemd/system/watchdog-web.service << EOF
[Unit]
Description=Watchdog Web
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable watchdog watchdog-web > /dev/null 2>&1
    
    print_ok "Services configured"
}

# ============================================================================
# Start services
# ============================================================================

start_services() {
    print_step "Starting services..."
    
    systemctl restart watchdog
    sleep 2
    systemctl restart watchdog-web
    sleep 2
    
    print_ok "Services started"
}

# ============================================================================
# Main
# ============================================================================

main() {
    # Check root
    if [ "$EUID" -ne 0 ]; then
        print_error "Run as root: sudo bash install.sh"
        exit 1
    fi
    
    detect_system
    check_existing
    install_dependencies
    install_files
    configure_network
    create_config
    create_admin
    setup_services
    start_services
    
    # Done
    IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}              INSTALLATION COMPLETE!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  Web: ${CYAN}http://${IP}/${NC}"
    echo ""
    echo -e "  Login: ${GREEN}admin${NC} / ${GREEN}${ADMIN_PASS:-admin}${NC}"
    echo ""
    
    if [ "$NETWORK_CONFIGURED" = true ]; then
        echo -e "  ${YELLOW}⚠️  Static IP will be active after reboot${NC}"
        echo ""
        read -p "Reboot now? (y/N): " DO_REBOOT
        [[ "$DO_REBOOT" =~ ^[Yy]$ ]] && reboot
    fi
}

main "$@"

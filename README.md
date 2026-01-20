# Watchdog v1.0

**Network Monitoring System with Automatic Power Reset**

Watchdog monitors network devices and automatically restarts unresponsive equipment via GPIO-controlled power outlets (SSR relays).

[![Version](https://img.shields.io/badge/version-1.0-blue)](https://github.com/MaraXa-CZ/watchdog/releases)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red)

## Features

- 🔍 **Network Monitoring** - Ping, HTTP, TCP port checks
- ⚡ **Automatic Reset** - GPIO-controlled SSR relay switching
- 📊 **Statistics** - Response time charts, availability history
- 👥 **Multi-User** - Admin, Operator, Viewer roles
- 🌍 **Multi-Language** - English, Czech
- 📱 **Mobile App** - PWA for iOS/Android
- 🔒 **Security** - SSL/HTTPS, audit logging

## Supported Hardware

| Raspberry Pi | Status |
|--------------|--------|
| Pi 5 | ✅ Full support |
| Pi 4 / 400 | ✅ Full support |
| Pi 3 / Zero 2 | ✅ Full support |
| Pi 2 | ✅ Full support |
| Pi 1 / Zero | ⚠️ Limited (slower) |

## Supported OS

| OS | Version | Status |
|----|---------|--------|
| Raspberry Pi OS | Bullseye (11) | ✅ |
| Raspberry Pi OS | Bookworm (12) | ✅ |
| Raspberry Pi OS | Trixie (13) | ✅ |
| Ubuntu Server | 22.04 / 24.04 | ✅ |

## Installation

```bash
cd /opt
sudo git clone https://github.com/MaraXa-CZ/watchdog.git
cd watchdog
sudo bash install.sh
```

The installer will:
1. Install dependencies (Flask, GPIO libraries)
2. Optionally configure static IP
3. Create admin user
4. Start services

## First Login

- **URL**: `http://<raspberry-ip>/`
- **Username**: `admin`
- **Password**: (set during installation, default: `admin`)

⚠️ **Change the default password immediately!**

## Update

```bash
cd /opt/watchdog
sudo git pull
sudo bash install.sh
sudo systemctl restart watchdog watchdog-web
```

## Wiring

### Basic Setup (1 SSR)

```
Raspberry Pi          SSR Relay
────────────          ─────────
GPIO 17  ──────────►  DC+ (3-32V)
GND      ──────────►  DC-

                      AC Load ──► Device
                      AC Live ◄── Mains L
```

### Recommended GPIO Pins

| GPIO | Pin | Safe to use |
|------|-----|-------------|
| 17, 18, 27, 22 | 11, 12, 13, 15 | ✅ Yes |
| 23, 24, 25, 26 | 16, 18, 22, 37 | ✅ Yes |
| 5, 6, 12, 13, 16 | 29, 31, 32, 33, 36 | ✅ Yes |

## Service Management

```bash
# Status
sudo systemctl status watchdog watchdog-web

# Restart
sudo systemctl restart watchdog watchdog-web

# Logs
journalctl -u watchdog -f
journalctl -u watchdog-web -f
```

## Reset Password

```bash
sudo bash /opt/watchdog/reset_password.sh
```

## Uninstall

```bash
sudo bash /opt/watchdog/uninstall.sh
```

## API

```bash
# Login
curl -X POST http://watchdog/api/auth \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Get groups
curl http://watchdog/api/groups \
  -H "Authorization: Bearer <token>"

# Control relay
curl -X POST http://watchdog/api/control \
  -H "Authorization: Bearer <token>" \
  -d '{"group": "Servers", "action": "restart"}'
```

## License

MIT License - see [LICENSE.txt](LICENSE.txt)

## Author

© 2025 MaraXa

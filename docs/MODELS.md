# Watchdog v1.0 - Raspberry Pi Models

> 🔧 **Podrobné informace o kompatibilitě OS a GPIO knihovnách:** [COMPATIBILITY.md](COMPATIBILITY.md)

## Supported Raspberry Pi Models

| Model | CPU | RAM | GPIO Pins | Supported OS | Watchdog Support |
|-------|-----|-----|-----------|--------------|------------------|
| **Raspberry Pi 5** | Broadcom BCM2712, Quad-core Cortex-A76 @ 2.4GHz | 4GB / 8GB | 40 (26 usable) | Raspberry Pi OS Bookworm | ✅ Full |
| **Raspberry Pi 4 Model B** | Broadcom BCM2711, Quad-core Cortex-A72 @ 1.8GHz | 1GB / 2GB / 4GB / 8GB | 40 (26 usable) | Raspberry Pi OS Bullseye/Bookworm, Ubuntu 22.04+ | ✅ Full |
| **Raspberry Pi 400** | Broadcom BCM2711, Quad-core Cortex-A72 @ 1.8GHz | 4GB | 40 (26 usable) | Raspberry Pi OS Bullseye/Bookworm | ✅ Full |
| **Raspberry Pi 3 Model B+** | Broadcom BCM2837B0, Quad-core Cortex-A53 @ 1.4GHz | 1GB | 40 (26 usable) | Raspberry Pi OS Bullseye/Bookworm | ✅ Full |
| **Raspberry Pi 3 Model B** | Broadcom BCM2837, Quad-core Cortex-A53 @ 1.2GHz | 1GB | 40 (26 usable) | Raspberry Pi OS Bullseye/Bookworm | ✅ Full |
| **Raspberry Pi 3 Model A+** | Broadcom BCM2837B0, Quad-core Cortex-A53 @ 1.4GHz | 512MB | 40 (26 usable) | Raspberry Pi OS Bullseye/Bookworm | ✅ Full |
| **Raspberry Pi 2 Model B v1.2** | Broadcom BCM2837, Quad-core Cortex-A53 @ 900MHz | 1GB | 40 (26 usable) | Raspberry Pi OS Bullseye | ✅ Full |
| **Raspberry Pi 2 Model B** | Broadcom BCM2836, Quad-core Cortex-A7 @ 900MHz | 1GB | 40 (26 usable) | Raspberry Pi OS Bullseye | ✅ Full |
| **Raspberry Pi 1 Model B+** | Broadcom BCM2835, Single-core ARM1176JZF-S @ 700MHz | 512MB | 40 (26 usable) | Raspberry Pi OS Bullseye (32-bit) | ⚠️ Limited |
| **Raspberry Pi 1 Model B** | Broadcom BCM2835, Single-core ARM1176JZF-S @ 700MHz | 512MB | 26 (17 usable) | Raspberry Pi OS Bullseye (32-bit) | ⚠️ Limited |
| **Raspberry Pi 1 Model A+** | Broadcom BCM2835, Single-core ARM1176JZF-S @ 700MHz | 256MB / 512MB | 40 (26 usable) | Raspberry Pi OS Bullseye (32-bit) | ⚠️ Limited |
| **Raspberry Pi Zero 2 W** | Broadcom BCM2710A1, Quad-core Cortex-A53 @ 1GHz | 512MB | 40 (26 usable) | Raspberry Pi OS Bullseye/Bookworm | ✅ Full |
| **Raspberry Pi Zero W** | Broadcom BCM2835, Single-core ARM1176JZF-S @ 1GHz | 512MB | 40 (26 usable) | Raspberry Pi OS Bullseye (32-bit) | ⚠️ Limited |
| **Raspberry Pi Zero** | Broadcom BCM2835, Single-core ARM1176JZF-S @ 1GHz | 512MB | 40 (26 usable) | Raspberry Pi OS Bullseye (32-bit) | ⚠️ Limited |

## GPIO Pin Overview

### 40-Pin Header (Pi 1 B+, Pi 2, Pi 3, Pi 4, Pi 5, Zero)

```
                    3.3V  (1)  (2)  5V
          I2C SDA - GPIO2  (3)  (4)  5V
          I2C SCL - GPIO3  (5)  (6)  GND
                    GPIO4  (7)  (8)  GPIO14 - UART TX
                      GND  (9)  (10) GPIO15 - UART RX
                   GPIO17 (11)  (12) GPIO18 - PCM CLK
                   GPIO27 (13)  (14) GND
                   GPIO22 (15)  (16) GPIO23
                    3.3V (17)  (18) GPIO24
         SPI MOSI - GPIO10 (19)  (20) GND
         SPI MISO - GPIO9  (21)  (22) GPIO25
         SPI SCLK - GPIO11 (23)  (24) GPIO8  - SPI CE0
                      GND (25)  (26) GPIO7  - SPI CE1
          EEPROM  - GPIO0  (27)  (28) GPIO1  - EEPROM
                    GPIO5 (29)  (30) GND
                    GPIO6 (31)  (32) GPIO12
                   GPIO13 (33)  (34) GND
         PCM FS  - GPIO19 (35)  (36) GPIO16
                   GPIO26 (37)  (38) GPIO20 - PCM DIN
                      GND (39)  (40) GPIO21 - PCM DOUT
```

### Usable GPIO Pins for Watchdog SSR Control

| GPIO | Physical Pin | Status | Notes |
|------|--------------|--------|-------|
| GPIO4 | 7 | ✅ **Recommended** | General purpose |
| GPIO5 | 29 | ✅ **Recommended** | General purpose |
| GPIO6 | 31 | ✅ **Recommended** | General purpose |
| GPIO12 | 32 | ✅ **Recommended** | General purpose |
| GPIO13 | 33 | ✅ **Recommended** | General purpose |
| GPIO16 | 36 | ✅ **Recommended** | General purpose |
| GPIO17 | 11 | ✅ **Recommended** | General purpose |
| GPIO18 | 12 | ✅ **Recommended** | PWM capable |
| GPIO19 | 35 | ✅ **Recommended** | General purpose |
| GPIO20 | 38 | ✅ **Recommended** | General purpose |
| GPIO21 | 40 | ✅ **Recommended** | General purpose |
| GPIO22 | 15 | ✅ **Recommended** | General purpose |
| GPIO23 | 16 | ✅ **Recommended** | General purpose |
| GPIO24 | 18 | ✅ **Recommended** | General purpose |
| GPIO25 | 22 | ✅ **Recommended** | General purpose |
| GPIO26 | 37 | ✅ **Recommended** | General purpose |
| GPIO27 | 13 | ✅ **Recommended** | General purpose |
| GPIO2 | 3 | ⚠️ I2C SDA | Use if I2C not needed |
| GPIO3 | 5 | ⚠️ I2C SCL | Use if I2C not needed |
| GPIO14 | 8 | ⚠️ UART TX | Use if UART not needed |
| GPIO15 | 10 | ⚠️ UART RX | Use if UART not needed |
| GPIO7-11 | Various | ⚠️ SPI | Use if SPI not needed |
| GPIO0-1 | 27-28 | ❌ Reserved | EEPROM, do not use |

## Supported Operating Systems

| OS | Version | Architecture | Watchdog Support |
|----|---------|--------------|------------------|
| **Raspberry Pi OS** | Bookworm (12) | 32-bit / 64-bit | ✅ Recommended |
| **Raspberry Pi OS** | Bullseye (11) | 32-bit / 64-bit | ✅ Full Support |
| **Raspberry Pi OS** | Buster (10) | 32-bit / 64-bit | ⚠️ Legacy (Python 3.7) |
| **Ubuntu Server** | 22.04 LTS | 64-bit | ✅ Full Support |
| **Ubuntu Server** | 24.04 LTS | 64-bit | ✅ Full Support |
| **DietPi** | 8.x+ | 32-bit / 64-bit | ✅ Full Support |
| **Armbian** | Latest | 64-bit | ✅ Full Support |

## Requirements

### Minimum Requirements
- **Python**: 3.9+
- **RAM**: 256MB (512MB+ recommended)
- **Storage**: 100MB free space
- **Network**: Ethernet or WiFi

### GPIO Library by Platform

| Pi Model | GPIO Library | Notes |
|----------|--------------|-------|
| Pi 1, 2, 3, Zero | RPi.GPIO | Standard library |
| Pi 4 | RPi.GPIO | Standard library |
| Pi 5 | lgpio / gpiod | New kernel interface |

### Pi 5 Special Notes

Raspberry Pi 5 uses a different GPIO chip (RP1) and requires:
- `lgpio` library instead of `RPi.GPIO`
- Kernel 6.1+ with gpiochip support

Watchdog automatically detects Pi 5 and uses appropriate library.

## Performance Comparison

| Model | Ping Check Speed | Web UI Response | Max Recommended Groups |
|-------|------------------|-----------------|------------------------|
| Pi Zero | ~500ms | ~200ms | 4 |
| Pi Zero 2 W | ~200ms | ~100ms | 8 |
| Pi 3 | ~150ms | ~80ms | 8 |
| Pi 4 | ~100ms | ~50ms | 16 |
| Pi 5 | ~80ms | ~30ms | 16 |

## Legend

- ✅ **Full Support** - All features work, recommended
- ⚠️ **Limited** - Works but may be slow or have limitations
- ❌ **Not Supported** - Will not work

---

*Watchdog v1.0 - © 2026 MaraXa*

## Trixie (Debian 13+) Support

Watchdog v1.0 includes full support for Raspberry Pi OS Trixie:

| Feature | Status |
|---------|--------|
| GPIO via gpiod | ✅ Full |
| NetworkManager | ✅ Full |
| Python venv | ✅ Required |
| Pi 5 | ✅ Full |

### Automatic Backend Detection

Watchdog automatically selects the best GPIO backend:

```
OS Version >= 13 (Trixie+):
    └─ Try gpiod → lgpio → gpiozero

Pi 5 on Bookworm:
    └─ Try lgpio → gpiod → gpiozero

Pi 1-4 on older OS:
    └─ Try gpiozero → lgpio → gpiod
```

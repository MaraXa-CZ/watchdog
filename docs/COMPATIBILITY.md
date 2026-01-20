# Watchdog v1.0 - Systémové nároky a kompatibilita

> 📋 **Podrobný přehled všech modelů Raspberry Pi včetně CPU, RAM a GPIO:** [MODELS.md](MODELS.md)

## Podporované Raspberry Pi modely

| Model | Architektura | Status | Poznámka |
|-------|--------------|--------|----------|
| Raspberry Pi 1 Model A/B/B+ | ARMv6 (ARM11) | ✅ Plně podporováno | Vyžaduje Bullseye Legacy 32-bit |
| Raspberry Pi Zero / Zero W | ARMv6 (ARM11) | ✅ Plně podporováno | Vyžaduje Bullseye Legacy 32-bit |
| Raspberry Pi 2 Model B | ARMv7 | ✅ Plně podporováno | |
| Raspberry Pi 3 Model A+/B/B+ | ARMv8 | ✅ Plně podporováno | |
| Raspberry Pi Zero 2 W | ARMv8 | ✅ Plně podporováno | |
| Raspberry Pi 4 Model B | ARMv8 | ✅ Plně podporováno | |
| Raspberry Pi 400 | ARMv8 | ✅ Plně podporováno | |
| Raspberry Pi 5 | ARMv8 | ⚠️ Vyžaduje úpravy | Viz sekce Pi 5 níže |

---

## Podporované operační systémy

### Primární podpora (testováno)

| OS | Verze | Architektura | Pi modely | Status |
|----|-------|--------------|-----------|--------|
| Raspberry Pi OS | Bullseye Legacy | 32-bit | Pi 1, Zero, 2, 3, 4 | ✅ Doporučeno pro Pi 1 |
| Raspberry Pi OS | Bullseye | 32-bit | Pi 2, 3, 4 | ✅ Plně podporováno |
| Raspberry Pi OS | Bullseye | 64-bit | Pi 3, 4 | ✅ Plně podporováno |
| Raspberry Pi OS | Bookworm | 32-bit | Pi 2, 3, 4 | ✅ Plně podporováno |
| Raspberry Pi OS | Bookworm | 64-bit | Pi 3, 4, 5 | ⚠️ Pi 5 vyžaduje úpravy |

### Doporučená konfigurace dle modelu

```
Pi 1 / Zero (ARMv6):     Bullseye Legacy 32-bit (Lite)
Pi 2:                    Bullseye nebo Bookworm 32-bit (Lite)
Pi 3 / Zero 2 W:         Bookworm 64-bit (Lite)
Pi 4 / 400:              Bookworm 64-bit (Lite)
Pi 5:                    Bookworm 64-bit (Lite) + úpravy GPIO
```

**Doporučujeme Lite verzi** (bez desktopu) pro minimální spotřebu zdrojů.

---

## Softwarové požadavky

### Minimální verze

| Software | Minimální verze | Poznámka |
|----------|-----------------|----------|
| Python | 3.9+ | Bullseye má 3.9, Bookworm má 3.11 |
| pip | 20.0+ | |
| gpiozero | 1.6+ | |
| Flask | 2.0+ | |
| Werkzeug | 2.0+ | |

### GPIO knihovny dle Pi modelu

| Pi Model | GPIO Backend | Knihovna |
|----------|--------------|----------|
| Pi 1-4 | RPi.GPIO | `pip install RPi.GPIO` |
| Pi 5 | lgpio | `pip install lgpio` |

---

## Raspberry Pi 5 - Specifické úpravy

Pi 5 má **nový GPIO řadič RP1** který není kompatibilní s klasickým RPi.GPIO.

### Co je potřeba změnit pro Pi 5:

#### 1. Instalace lgpio místo RPi.GPIO

```bash
# Na Pi 5 - Bookworm
sudo apt install python3-lgpio
pip install lgpio --break-system-packages
```

#### 2. Úprava gpio_manager.py

Změnit import na začátku souboru:

```python
# PŮVODNÍ (Pi 1-4):
try:
    from gpiozero import OutputDevice
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

# NOVÉ (Pi 5 kompatibilní):
try:
    from gpiozero import OutputDevice
    from gpiozero.pins.lgpio import LGPIOFactory
    from gpiozero import Device
    
    # Na Pi 5 použij lgpio backend
    import os
    if os.path.exists('/proc/device-tree/model'):
        with open('/proc/device-tree/model') as f:
            if 'Pi 5' in f.read():
                Device.pin_factory = LGPIOFactory()
    
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
```

#### 3. Úprava install.sh

Přidat detekci Pi 5 a instalaci lgpio:

```bash
# Detekce Pi 5
if grep -q "Pi 5" /proc/device-tree/model 2>/dev/null; then
    echo "Raspberry Pi 5 detekován - instaluji lgpio..."
    apt-get install -y python3-lgpio
    "$INSTALL_DIR/venv/bin/pip" install lgpio
fi
```

### Alternativní řešení pro Pi 5

Místo gpiozero lze použít přímo **lgpio**:

```python
import lgpio

# Otevření GPIO chipu
chip = lgpio.gpiochip_open(0)

# Nastavení pinu jako výstup
lgpio.gpio_claim_output(chip, 17)

# Zapnutí/vypnutí
lgpio.gpio_write(chip, 17, 1)  # ON
lgpio.gpio_write(chip, 17, 0)  # OFF

# Uzavření
lgpio.gpiochip_close(chip)
```

---

## Hardwarové nároky

### Minimální

| Parametr | Hodnota |
|----------|---------|
| RAM | 256 MB (Pi 1) |
| Storage | 2 GB microSD |
| CPU | Single-core 700 MHz (Pi 1) |

### Doporučené

| Parametr | Hodnota |
|----------|---------|
| RAM | 512 MB+ |
| Storage | 8 GB+ microSD Class 10 |
| CPU | Quad-core (Pi 3/4) |

### Spotřeba

| Model | Idle | Při monitoringu |
|-------|------|-----------------|
| Pi 1 B | ~2W | ~2.5W |
| Pi Zero W | ~0.8W | ~1.2W |
| Pi 3 B+ | ~2.5W | ~3W |
| Pi 4 (2GB) | ~3W | ~4W |
| Pi 5 | ~4W | ~5W |

---

## Známé problémy a řešení

### Pi 1 / Zero - Pomalý start

**Problém:** Flask může startovat 30-60 sekund na ARMv6.

**Řešení:** Zvýšit timeout v systemd službě:
```ini
[Service]
TimeoutStartSec=120
```

### Pi 5 - GPIO nefunguje

**Problém:** `RuntimeError: Cannot determine SOC peripheral base address`

**Řešení:** Viz sekce "Raspberry Pi 5 - Specifické úpravy" výše.

### Bookworm - pip instalace selhává

**Problém:** `error: externally-managed-environment`

**Řešení:** Použít `--break-system-packages` flag nebo virtuální prostředí (install.sh to řeší automaticky).

### Všechny modely - Nedostatečná paměť

**Problém:** Na Pi 1/Zero s 256-512MB RAM může dojít paměť.

**Řešení:** 
```bash
# Zvýšit swap
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=512/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

---

## Matice kompatibility - Shrnutí

```
                    │ Bullseye  │ Bullseye │ Bookworm │ Bookworm │
                    │ Legacy 32 │ 32/64    │ 32       │ 64       │
────────────────────┼───────────┼──────────┼──────────┼──────────┤
Pi 1 / Zero         │    ✅     │    ❌    │    ❌    │    ❌    │
Pi 2                │    ✅     │    ✅    │    ✅    │    ❌    │
Pi 3 / Zero 2 W     │    ✅     │    ✅    │    ✅    │    ✅    │
Pi 4 / 400          │    ✅     │    ✅    │    ✅    │    ✅    │
Pi 5                │    ❌     │    ❌    │    ❌    │   ⚠️*    │

* Pi 5 vyžaduje úpravu GPIO knihovny (lgpio místo RPi.GPIO)
```

---

## Doporučení

1. **Pro maximální kompatibilitu (Pi 1-4):** Použij **Bullseye Legacy 32-bit Lite**
2. **Pro moderní Pi (3-4):** Použij **Bookworm 64-bit Lite**
3. **Pro Pi 5:** Počkej na oficiální verzi s lgpio nebo proveď úpravy dle návodu výše

---

© 2026 MaraXa - Watchdog v1.0

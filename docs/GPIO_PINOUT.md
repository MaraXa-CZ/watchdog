# Watchdog v4.0 - GPIO Pinout Reference

## Podporované GPIO piny

Watchdog v4.0 podporuje až **16 zásuvek** pomocí GPIO pinů Raspberry Pi.

### Doporučené piny (bezpečné)

Tyto piny nemají žádné speciální funkce a jsou bezpečné pro použití:

| GPIO | Fyzický pin | Poznámka |
|------|-------------|----------|
| 4    | 7           | GPCLK0 (lze použít) |
| 5    | 29          | ✓ Obecný GPIO |
| 6    | 31          | ✓ Obecný GPIO |
| 12   | 32          | PWM0 (lze použít) |
| 13   | 33          | PWM1 (lze použít) |
| 16   | 36          | ✓ Obecný GPIO |
| 17   | 11          | ✓ Obecný GPIO |
| 18   | 12          | PCM_CLK (lze použít) |
| 19   | 35          | PCM_FS (lze použít) |
| 20   | 38          | PCM_DIN (lze použít) |
| 21   | 40          | PCM_DOUT (lze použít) |
| 22   | 15          | ✓ Obecný GPIO |
| 23   | 16          | ✓ Obecný GPIO |
| 24   | 18          | ✓ Obecný GPIO |
| 25   | 22          | ✓ Obecný GPIO |
| 26   | 37          | ✓ Obecný GPIO |
| 27   | 13          | ✓ Obecný GPIO |

### Piny s alternativními funkcemi

Tyto piny lze použít, ale mají speciální funkce které budou deaktivovány:

| GPIO | Fyzický pin | Alternativní funkce | Lze použít pokud... |
|------|-------------|---------------------|---------------------|
| 2    | 3           | I2C SDA             | Nepoužíváte I2C |
| 3    | 5           | I2C SCL             | Nepoužíváte I2C |
| 7    | 26          | SPI CE1             | Nepoužíváte SPI |
| 8    | 24          | SPI CE0             | Nepoužíváte SPI |
| 9    | 21          | SPI MISO            | Nepoužíváte SPI |
| 10   | 19          | SPI MOSI            | Nepoužíváte SPI |
| 11   | 23          | SPI SCLK            | Nepoužíváte SPI |
| 14   | 8           | UART TXD            | Nepoužíváte sériovou konzoli |
| 15   | 10          | UART RXD            | Nepoužíváte sériovou konzoli |

### Piny které NEPOUŽÍVAT

| GPIO | Důvod |
|------|-------|
| 0, 1 | Rezervováno pro HAT EEPROM |

## Fyzické zapojení

```
┌───────────────────────────────────────────────────────────────┐
│                  Raspberry Pi GPIO Header (J8)                │
│                         (pohled shora)                        │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│   3V3  (1)  ●  ●  (2)  5V                                     │
│   SDA  (3)  ●  ●  (4)  5V        ← GPIO 2 (I2C)               │
│   SCL  (5)  ●  ●  (6)  GND       ← GPIO 3 (I2C)               │
│   GP4  (7)  ●  ●  (8)  TXD       ← GPIO 4 ✓, GPIO 14 (UART)   │
│   GND  (9)  ●  ●  (10) RXD       ← GPIO 15 (UART)             │
│  GP17 (11)  ●  ●  (12) GP18      ← GPIO 17 ✓, GPIO 18 ✓       │
│  GP27 (13)  ●  ●  (14) GND       ← GPIO 27 ✓                  │
│  GP22 (15)  ●  ●  (16) GP23      ← GPIO 22 ✓, GPIO 23 ✓       │
│   3V3 (17)  ●  ●  (18) GP24      ← GPIO 24 ✓                  │
│  MOSI (19)  ●  ●  (20) GND       ← GPIO 10 (SPI)              │
│  MISO (21)  ●  ●  (22) GP25      ← GPIO 9 (SPI), GPIO 25 ✓    │
│  SCLK (23)  ●  ●  (24) CE0       ← GPIO 11 (SPI), GPIO 8 (SPI)│
│   GND (25)  ●  ●  (26) CE1       ← GPIO 7 (SPI)               │
│   ID  (27)  ●  ●  (28) ID        ← Nepoužívat (EEPROM)        │
│   GP5 (29)  ●  ●  (30) GND       ← GPIO 5 ✓                   │
│   GP6 (31)  ●  ●  (32) GP12      ← GPIO 6 ✓, GPIO 12 ✓        │
│  GP13 (33)  ●  ●  (34) GND       ← GPIO 13 ✓                  │
│  GP19 (35)  ●  ●  (36) GP16      ← GPIO 19 ✓, GPIO 16 ✓       │
│  GP26 (37)  ●  ●  (38) GP20      ← GPIO 26 ✓, GPIO 20 ✓       │
│   GND (39)  ●  ●  (40) GP21      ← GPIO 21 ✓                  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Příklad konfigurace pro 8 relé

```json
{
  "outlets": {
    "outlet_1": {"name": "Server Rack 1", "gpio_pin": 17},
    "outlet_2": {"name": "Server Rack 2", "gpio_pin": 18},
    "outlet_3": {"name": "Switch A", "gpio_pin": 27},
    "outlet_4": {"name": "Switch B", "gpio_pin": 22},
    "outlet_5": {"name": "Router", "gpio_pin": 23},
    "outlet_6": {"name": "NAS", "gpio_pin": 24},
    "outlet_7": {"name": "UPS Monitor", "gpio_pin": 25},
    "outlet_8": {"name": "Backup Server", "gpio_pin": 5}
  }
}
```

## Příklad konfigurace pro 16 relé (maximum)

```json
{
  "outlets": {
    "outlet_1":  {"name": "Rack 1",  "gpio_pin": 17},
    "outlet_2":  {"name": "Rack 2",  "gpio_pin": 18},
    "outlet_3":  {"name": "Rack 3",  "gpio_pin": 27},
    "outlet_4":  {"name": "Rack 4",  "gpio_pin": 22},
    "outlet_5":  {"name": "Rack 5",  "gpio_pin": 23},
    "outlet_6":  {"name": "Rack 6",  "gpio_pin": 24},
    "outlet_7":  {"name": "Rack 7",  "gpio_pin": 25},
    "outlet_8":  {"name": "Rack 8",  "gpio_pin": 5},
    "outlet_9":  {"name": "Rack 9",  "gpio_pin": 6},
    "outlet_10": {"name": "Rack 10", "gpio_pin": 12},
    "outlet_11": {"name": "Rack 11", "gpio_pin": 13},
    "outlet_12": {"name": "Rack 12", "gpio_pin": 16},
    "outlet_13": {"name": "Rack 13", "gpio_pin": 19},
    "outlet_14": {"name": "Rack 14", "gpio_pin": 20},
    "outlet_15": {"name": "Rack 15", "gpio_pin": 21},
    "outlet_16": {"name": "Rack 16", "gpio_pin": 26}
  }
}
```

## Zapojení SSR relé

Pro každý outlet:

```
Raspberry Pi          SSR Relé           Zásuvka 230V
─────────────         ────────           ────────────
GPIO pin ─────────────→ + (DC+)
GND      ─────────────→ - (DC-)

                      AC Live ─────────→ L (fáze)
                      AC Load ─────────→ Spotřebič
                      
                      N (nulák) ────────→ přímo na spotřebič
```

### Doporučená SSR relé:

| Model | Max proud | Ovládací napětí | Cena |
|-------|-----------|-----------------|------|
| Fotek SSR-25DA | 25A | 3-32V DC | ~100 Kč |
| Fotek SSR-40DA | 40A | 3-32V DC | ~150 Kč |
| Omron G3MB-202P | 2A | 5V DC | ~50 Kč |

**⚠️ VAROVÁNÍ:** Práce s 230V je nebezpečná! Vždy odpojte napájení před úpravami.

## Kompatibilita s Raspberry Pi

| Model | Max GPIO | Poznámka |
|-------|----------|----------|
| Pi 1 / Zero | 26 | Plná podpora |
| Pi 2 | 26 | Plná podpora |
| Pi 3 / Zero 2 W | 26 | Plná podpora |
| Pi 4 / 400 | 26 | Plná podpora |
| Pi 5 | 26 | Vyžaduje lgpio backend |

Viz [COMPATIBILITY.md](COMPATIBILITY.md) pro detaily.

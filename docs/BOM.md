# Watchdog v3.0 - Bill of Materials (BOM)
# © 2026 MaraXa

================================================================================
                          SEZNAM MATERIÁLU (BOM)
================================================================================

## EASY MODE (1x SSR)
--------------------------------------------------------------------------------
| #  | Položka                      | Množství | Poznámka                      |
|----|------------------------------|----------|-------------------------------|
| 1  | Raspberry Pi                 | 1 ks     | Jakýkoliv model s GPIO        |
| 2  | microSD karta                | 1 ks     | Min. 8GB, Class 10            |
| 3  | Napájecí zdroj RPi           | 1 ks     | 5V 3A USB-C nebo microUSB     |
| 4  | SSR relé                     | 1 ks     | Fotek SSR-25DA nebo ekviv.    |
| 5  | Zásuvka 230V                 | 1 ks     | Vestavná nebo na povrch       |
| 6  | Rozvodná krabice             | 1 ks     | Min. 100x100x50mm             |
| 7  | Vodiče 1.5mm²                | 1 m      | Pro 230V rozvody              |
| 8  | Dupont kabely F-F            | 3 ks     | Pro GPIO připojení            |
| 9  | Svorkovnice                  | 2 ks     | Pro 230V spoje                |
| 10 | Ethernet kabel               | 1 ks     | Dle potřeby, nebo WiFi        |
--------------------------------------------------------------------------------

Odhadovaná cena Easy Mode: 800 - 1200 Kč (bez RPi)


## FULL MODE (4x SSR)
--------------------------------------------------------------------------------
| #  | Položka                      | Množství | Poznámka                      |
|----|------------------------------|----------|-------------------------------|
| 1  | Raspberry Pi                 | 1 ks     | Jakýkoliv model s GPIO        |
| 2  | microSD karta                | 1 ks     | Min. 8GB, Class 10            |
| 3  | Napájecí zdroj RPi           | 1 ks     | 5V 3A USB-C nebo microUSB     |
| 4  | SSR relé                     | 4 ks     | Fotek SSR-25DA nebo ekviv.    |
| 5  | Zásuvka 230V                 | 4 ks     | Vestavná nebo na povrch       |
| 6  | Rozvodná krabice             | 1 ks     | Min. 200x150x100mm            |
| 7  | Vodiče 1.5mm²                | 3 m      | Pro 230V rozvody              |
| 8  | Dupont kabely F-F            | 10 ks    | Pro GPIO připojení            |
| 9  | Svorkovnice                  | 8 ks     | Pro 230V spoje                |
| 10 | DIN lišta                    | 1 ks     | 200mm, pro montáž SSR         |
| 11 | Chladič pro SSR              | 4 ks     | Při zátěži > 5A               |
| 12 | Ethernet kabel               | 1 ks     | Dle potřeby, nebo WiFi        |
| 13 | Jistič 10A                   | 1 ks     | Ochrana obvodu                |
--------------------------------------------------------------------------------

Odhadovaná cena Full Mode: 1800 - 2500 Kč (bez RPi)


## DOPORUČENÉ SOUČÁSTKY
--------------------------------------------------------------------------------

### SSR Relé (Solid State Relay)
- **Doporučeno:** Fotek SSR-25DA
  - DC Input: 3-32V
  - AC Output: 24-380V, 25A
  - Zero-cross switching
  - Cena: cca 150-250 Kč/ks

- **Alternativy:**
  - Omron G3MB-202P (2A max)
  - Crydom D2425 (25A, prémiová kvalita)
  - Generic SSR-40DA (40A, větší rezerva)

### Raspberry Pi
- **Doporučeno:** Raspberry Pi 4 Model B (2GB+)
- **Alternativy:** 
  - Raspberry Pi 3B+ (dostačující)
  - Raspberry Pi Zero 2 W (kompaktní)
  - Raspberry Pi 5 (nejvyšší výkon)

### microSD karta
- **Doporučeno:** SanDisk Extreme 32GB
- **Alternativy:**
  - Samsung EVO Plus
  - Kingston Canvas Select Plus

### Rozvodná krabice
- **Easy Mode:** 100x100x50mm, IP54
- **Full Mode:** 200x150x100mm, IP54
- S možností montáže DIN lišty

### Vodiče
- **230V:** CYA 1.5mm² (min.), ideálně 2.5mm²
- **GPIO:** Dupont kabely nebo vodiče 0.5mm²
- Barvy: L=hnědá, N=modrá, PE=žluto-zelená


## NÁSTROJE PRO INSTALACI
--------------------------------------------------------------------------------
| Nástroj                      | Použití                                       |
|------------------------------|-----------------------------------------------|
| Šroubovák křížový            | Montáž svorkovnic                             |
| Šroubovák plochý             | Připojení vodičů                              |
| Kleště na kabely             | Stříhání a odizolování                        |
| Zkoušečka napětí             | Kontrola napětí                               |
| Multimetr                    | Měření a diagnostika                          |
| Vrtačka                      | Montáž krabice (dle potřeby)                  |
| Stahovací pásky              | Organizace kabeláže                           |
--------------------------------------------------------------------------------


## POZNÁMKY
--------------------------------------------------------------------------------

1. BEZPEČNOST
   - Vždy pracujte s odpojeným napájením
   - Používejte odpovídající jištění
   - Dodržujte elektrotechnické normy ČSN

2. DIMENZOVÁNÍ SSR
   - SSR by mělo mít 2x vyšší proud než max. zátěž
   - Při zátěži > 5A použijte chladič
   - Zvažte aktivní chlazení při trvalé zátěži > 10A

3. KABELY GPIO
   - Délka max. 20cm pro spolehlivý signál
   - Při delších vzdálenostech použijte stíněné kabely

4. ZEMNĚNÍ
   - Raspberry Pi a SSR musí sdílet společnou zem (GND)
   - 230V strana musí být řádně uzemněna (PE)

================================================================================
                    Watchdog v3.0 | © 2026 MaraXa
================================================================================

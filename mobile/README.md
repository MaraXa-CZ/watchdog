# Watchdog Mobile App v4.0

React Native companion aplikace pro Watchdog Network Monitoring System.

## 📱 Funkce

- **Dashboard** - přehled všech aktivních skupin serverů
- **Live statistiky** - uptime %, počet resetů
- **Ovládání relé** - zapnutí/vypnutí/restart (dle oprávnění)
- **Multi-language** - čeština a angličtina
- **Dark/Light mode** - přepínání motivu
- **Offline first** - ukládání nastavení lokálně

## 🛠️ Požadavky

- Node.js 18+
- npm nebo yarn
- Expo CLI
- Android Studio (pro Android build)
- Xcode (pro iOS build, pouze macOS)

## 🚀 Instalace a spuštění

### Vývoj (Expo)

```bash
# Instalace závislostí
cd mobile
npm install

# Spuštění vývojového serveru
npx expo start

# Spuštění na konkrétní platformě
npx expo start --android
npx expo start --ios
```

### Build pro produkci

#### Android APK

```bash
# Instalace EAS CLI
npm install -g eas-cli

# Login do Expo účtu
eas login

# Build APK
eas build --platform android --profile preview
```

#### iOS App

```bash
# Build pro iOS (vyžaduje Apple Developer účet)
eas build --platform ios
```

## ⚙️ Konfigurace

Při prvním spuštění zadejte:

1. **URL serveru** - adresa Watchdog serveru (např. `http://192.168.1.100` nebo `https://watchdog.example.com`)
2. **Uživatelské jméno** - váš login
3. **Heslo** - vaše heslo

Aplikace automaticky získá API token a uloží ho pro další použití.

## 🔐 Oprávnění

Funkce v aplikaci se zobrazují dle role uživatele:

| Funkce | Admin | Operator | Viewer |
|--------|-------|----------|--------|
| Dashboard | ✅ | ✅ | ✅ |
| Statistiky | ✅ | ✅ | ✅ |
| Ovládání relé | ✅ | ✅ | ❌ |
| Nastavení účtu | ✅ | ✅ | ✅ |

## 📁 Struktura projektu

```
mobile/
├── App.js          # Hlavní komponenta aplikace
├── package.json    # Závislosti
├── app.json        # Expo konfigurace
├── assets/         # Ikony a splash screen
│   ├── icon.png
│   ├── splash.png
│   └── adaptive-icon.png
└── README.md       # Tento soubor
```

## 🎨 Přizpůsobení

### Ikony

Nahraďte soubory v `assets/`:
- `icon.png` - 1024x1024px, hlavní ikona
- `splash.png` - 1284x2778px, úvodní obrazovka
- `adaptive-icon.png` - 1024x1024px, Android adaptive icon

### Barvy

Barvy jsou definované v `App.js` v objektu `themes`:

```javascript
const themes = {
  dark: {
    background: '#1e1e1e',
    accent: '#0e7c7b',
    // ...
  },
  light: {
    background: '#f5f5f5',
    accent: '#0e7c7b',
    // ...
  },
};
```

## 🔧 Řešení problémů

### "Network request failed"

- Zkontrolujte, že server běží a je dostupný
- Ověřte správnost URL (včetně protokolu http/https)
- Na Androidu: povolte HTTP v development módu nebo použijte HTTPS

### "Invalid credentials"

- Ověřte uživatelské jméno a heslo
- Zkontrolujte, že účet není deaktivovaný

### Build selhává

```bash
# Vyčištění cache
npx expo start --clear
rm -rf node_modules
npm install
```

## 📄 Licence

Proprietární licence. Viz hlavní LICENSE.txt.

---

© 2026 MaraXa - Watchdog v4.0

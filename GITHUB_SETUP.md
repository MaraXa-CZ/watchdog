# GitHub Setup Instructions

## Repository

**URL**: https://github.com/MaraXa-CZ/watchdog

## Install on Raspberry Pi

### Fresh Install (via Git)

```bash
cd /opt
sudo git clone https://github.com/MaraXa-CZ/watchdog.git
cd watchdog
sudo bash install.sh
```

### Update Existing Installation

If already installed via Git:
```bash
cd /opt/watchdog
sudo git pull
sudo systemctl restart watchdog watchdog-web
```

Or use the **Updates** page in the web interface!

## Automatic Updates

Once installed via Git, users can:

1. Go to **Settings → Updates** in web interface
2. Click **Check for Updates**
3. If update available, click **Update**
4. System restarts automatically

---

## Creating New Releases

When you have a new version:

1. Update `VERSION` in `constants.py`
2. Update `VERSION` in `install.sh`
3. Update changelog in `README.md`
4. Commit changes:
   ```bash
   git add .
   git commit -m "Release v4.x.x"
   git push
   ```
5. Create release on GitHub with tag `v4.x.x`

---

## Repository Structure

```
watchdog/
├── app.py              # Web application
├── watchdog.py         # Monitoring daemon
├── constants.py        # Configuration constants
├── health_checker.py   # Ping/HTTP/TCP checks
├── updater.py          # GitHub auto-updater
├── users.py            # User management
├── i18n.py             # Internationalization
├── ...                 # Other modules
├── templates/          # HTML templates
├── mobile/             # PWA mobile app
├── schematics/         # Wiring diagrams
├── docs/               # Documentation
├── install.sh          # Installation script
├── README.md           # Main documentation
├── LICENSE.txt         # MIT License
└── .gitignore          # Git ignore rules
```

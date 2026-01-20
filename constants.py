"""
Watchdog v4.0 - Centralized Constants
=====================================
All configuration paths, limits, and defaults in one place.
Multi-user, multi-language, scheduled restarts support.
"""

import os

# Version
VERSION = "1.0"
VERSION_NAME = "Watchdog"
COPYRIGHT = "© 2026 MaraXa"

# GitHub repository for updates
GITHUB_REPO = "MaraXa-CZ/watchdog"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}"

# Paths
BASE_DIR = "/opt/watchdog"
INSTALL_DIR = BASE_DIR  # Alias for compatibility
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
AUDIT_FILE = os.path.join(BASE_DIR, "log", "audit.log")
STATS_DIR = os.path.join(BASE_DIR, "stats")
LOG_DIR = os.path.join(BASE_DIR, "log")
LOG_FILE = os.path.join(LOG_DIR, "watchdog.log")
COMMAND_DIR = os.path.join(BASE_DIR, "commands")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
VENV_DIR = os.path.join(BASE_DIR, "venv")
SSL_DIR = os.path.join(BASE_DIR, "ssl")
TRANSLATIONS_DIR = os.path.join(BASE_DIR, "translations")

# Limits
MAX_GROUPS = 16  # Increased for more outlets
MAX_SERVERS_PER_GROUP = 10
MAX_OUTLETS = 16  # Maximum number of power outlets
MAX_USERS = 50
MAX_LOG_SIZE_KB = 1024
DEFAULT_LOG_SIZE_KB = 512
MIN_CHECK_INTERVAL = 5
MAX_CHECK_INTERVAL = 300
DEFAULT_CHECK_INTERVAL = 10
MIN_FAIL_COUNT = 1
MAX_FAIL_COUNT = 10
DEFAULT_FAIL_COUNT = 3
MIN_OFF_TIME = 1
MAX_OFF_TIME = 60
DEFAULT_OFF_TIME = 10
DEFAULT_LOG_VIEW_LINES = 50
MAX_LOG_VIEW_LINES = 200

# Statistics
STATS_RETENTION_DAYS = 30
STATS_MAX_POINTS = 1000  # Max data points per group
STATS_INTERVAL_SECONDS = 60  # How often to record stats

# Health check types
CHECK_TYPE_PING = "ping"
CHECK_TYPE_HTTP = "http"
CHECK_TYPE_TCP = "tcp"
CHECK_TYPES = [CHECK_TYPE_PING, CHECK_TYPE_HTTP, CHECK_TYPE_TCP]

# Latency thresholds (ms)
DEFAULT_LATENCY_WARNING = 100
DEFAULT_LATENCY_CRITICAL = 500
MIN_LATENCY_THRESHOLD = 10
MAX_LATENCY_THRESHOLD = 5000

# Theme options
THEMES = ["dark", "light", "auto"]
DEFAULT_THEME = "dark"

# GPIO - All usable pins on Raspberry Pi (BCM numbering)
# Note: Some pins have alternate functions but can be used as GPIO
# GPIO 0, 1 - Reserved for HAT EEPROM (avoid)
# GPIO 2, 3 - I2C with pull-ups (can use if I2C not needed)
# GPIO 7-11 - SPI (can use if SPI not needed)
# GPIO 14, 15 - UART (can use if serial not needed)
VALID_GPIO_PINS = [
    # Safe general-purpose GPIO (recommended)
    4, 5, 6, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27,
    # I2C pins (usable if I2C not needed)
    2, 3,
    # SPI pins (usable if SPI not needed)
    7, 8, 9, 10, 11,
    # UART pins (usable if serial console not needed)
    14, 15
]

# GPIO pins organized by connector position (J8 header, left to right, top to bottom)
GPIO_PIN_INFO = {
    2:  {"name": "GPIO2/SDA1", "alt": "I2C Data", "safe": False},
    3:  {"name": "GPIO3/SCL1", "alt": "I2C Clock", "safe": False},
    4:  {"name": "GPIO4/GPCLK0", "alt": "General", "safe": True},
    5:  {"name": "GPIO5", "alt": "General", "safe": True},
    6:  {"name": "GPIO6", "alt": "General", "safe": True},
    7:  {"name": "GPIO7/CE1", "alt": "SPI CS1", "safe": False},
    8:  {"name": "GPIO8/CE0", "alt": "SPI CS0", "safe": False},
    9:  {"name": "GPIO9/MISO", "alt": "SPI MISO", "safe": False},
    10: {"name": "GPIO10/MOSI", "alt": "SPI MOSI", "safe": False},
    11: {"name": "GPIO11/SCLK", "alt": "SPI Clock", "safe": False},
    12: {"name": "GPIO12/PWM0", "alt": "PWM", "safe": True},
    13: {"name": "GPIO13/PWM1", "alt": "PWM", "safe": True},
    14: {"name": "GPIO14/TXD", "alt": "UART TX", "safe": False},
    15: {"name": "GPIO15/RXD", "alt": "UART RX", "safe": False},
    16: {"name": "GPIO16", "alt": "General", "safe": True},
    17: {"name": "GPIO17", "alt": "General", "safe": True},
    18: {"name": "GPIO18/PCM_CLK", "alt": "PCM/PWM", "safe": True},
    19: {"name": "GPIO19/PCM_FS", "alt": "PCM", "safe": True},
    20: {"name": "GPIO20/PCM_DIN", "alt": "PCM", "safe": True},
    21: {"name": "GPIO21/PCM_DOUT", "alt": "PCM", "safe": True},
    22: {"name": "GPIO22", "alt": "General", "safe": True},
    23: {"name": "GPIO23", "alt": "General", "safe": True},
    24: {"name": "GPIO24", "alt": "General", "safe": True},
    25: {"name": "GPIO25", "alt": "General", "safe": True},
    26: {"name": "GPIO26", "alt": "General", "safe": True},
    27: {"name": "GPIO27", "alt": "General", "safe": True}
}

# Default outlets - 8 pre-configured, user can add more
DEFAULT_GPIO_PINS = {
    "outlet_1": 17,
    "outlet_2": 18,
    "outlet_3": 27,
    "outlet_4": 22,
    "outlet_5": 23,
    "outlet_6": 24,
    "outlet_7": 25,
    "outlet_8": 5
}

# Network
DEFAULT_WEB_PORT = 80
DEFAULT_SSL_PORT = 443
MIN_WEB_PORT = 80
MAX_WEB_PORT = 65535
DEFAULT_DNS_SERVERS = ["8.8.8.8", "1.1.1.1"]
DEFAULT_NTP_SERVERS = ["pool.ntp.org", "time.google.com"]
DEFAULT_TIMEZONE = "Europe/Prague"

# Common timezones
TIMEZONES = [
    "Europe/Prague",
    "Europe/London",
    "Europe/Berlin",
    "Europe/Paris",
    "Europe/Rome",
    "Europe/Madrid",
    "Europe/Warsaw",
    "Europe/Vienna",
    "Europe/Amsterdam",
    "Europe/Brussels",
    "Europe/Stockholm",
    "Europe/Oslo",
    "Europe/Helsinki",
    "Europe/Athens",
    "Europe/Moscow",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Toronto",
    "America/Vancouver",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Singapore",
    "Asia/Dubai",
    "Australia/Sydney",
    "Pacific/Auckland",
    "UTC"
]

# Timeouts
PING_TIMEOUT = 1
PING_COUNT = 1
SERVICE_START_WAIT = 2
POST_RESET_WAIT = 30
AJAX_POLL_INTERVAL = 5000  # milliseconds

# SMTP Defaults
DEFAULT_SMTP_PORT = 587
DEFAULT_SMTP_TIMEOUT = 10

# Session
SESSION_LIFETIME_HOURS = 24
API_TOKEN_LIFETIME_DAYS = 365

# User Roles
ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"

ROLES = {
    ROLE_ADMIN: {
        "name_en": "Administrator",
        "name_cs": "Administrátor",
        "level": 100,
        "permissions": [
            "view_dashboard", "view_logs", "view_stats",
            "control_relays", "manage_groups", "manage_network",
            "manage_system", "manage_smtp", "manage_users",
            "manage_scheduler", "export_import", "view_audit"
        ]
    },
    ROLE_OPERATOR: {
        "name_en": "Operator",
        "name_cs": "Operátor",
        "level": 50,
        "permissions": [
            "view_dashboard", "view_logs", "view_stats",
            "control_relays", "manage_own_account"
        ]
    },
    ROLE_VIEWER: {
        "name_en": "Viewer",
        "name_cs": "Pozorovatel",
        "level": 10,
        "permissions": [
            "view_dashboard", "view_logs", "view_stats",
            "manage_own_account"
        ]
    }
}

# Supported Languages
LANGUAGES = {
    "cs": {"name": "Čeština", "flag": "🇨🇿"},
    "en": {"name": "English", "flag": "🇬🇧"}
}
DEFAULT_LANGUAGE = "cs"

# Scheduler - Days of week
DAYS_OF_WEEK = {
    0: {"en": "Monday", "cs": "Pondělí"},
    1: {"en": "Tuesday", "cs": "Úterý"},
    2: {"en": "Wednesday", "cs": "Středa"},
    3: {"en": "Thursday", "cs": "Čtvrtek"},
    4: {"en": "Friday", "cs": "Pátek"},
    5: {"en": "Saturday", "cs": "Sobota"},
    6: {"en": "Sunday", "cs": "Neděle"}
}

# File permissions
CONFIG_PERMISSIONS = 0o644
LOG_PERMISSIONS = 0o644

# Audit Event Types
AUDIT_LOGIN = "login"
AUDIT_LOGOUT = "logout"
AUDIT_LOGIN_FAILED = "login_failed"
AUDIT_CONFIG_CHANGE = "config_change"
AUDIT_USER_CHANGE = "user_change"
AUDIT_RELAY_CONTROL = "relay_control"
AUDIT_SCHEDULED_RESTART = "scheduled_restart"
AUDIT_AUTO_RESTART = "auto_restart"
AUDIT_PASSWORD_CHANGE = "password_change"

# Default config structure
DEFAULT_CONFIG = {
    "version": VERSION,
    "outlets": {
        "outlet_1": {"name": "Zásuvka 1", "gpio_pin": 17},
        "outlet_2": {"name": "Zásuvka 2", "gpio_pin": 18},
        "outlet_3": {"name": "Zásuvka 3", "gpio_pin": 27},
        "outlet_4": {"name": "Zásuvka 4", "gpio_pin": 22},
        "outlet_5": {"name": "Zásuvka 5", "gpio_pin": 23},
        "outlet_6": {"name": "Zásuvka 6", "gpio_pin": 24},
        "outlet_7": {"name": "Zásuvka 7", "gpio_pin": 25},
        "outlet_8": {"name": "Zásuvka 8", "gpio_pin": 5}
    },
    "max_groups": MAX_GROUPS,
    "groups": [],
    "check_interval": DEFAULT_CHECK_INTERVAL,
    "network": {
        "mode": "dhcp",
        "static_ip": "",
        "netmask": "255.255.255.0",
        "gateway": "",
        "dns_servers": DEFAULT_DNS_SERVERS
    },
    "system": {
        "hostname": "watchdog",
        "ntp_servers": DEFAULT_NTP_SERVERS,
        "timezone": DEFAULT_TIMEZONE,
        "web_port": DEFAULT_WEB_PORT,
        "ssl_enabled": False,
        "ssl_port": DEFAULT_SSL_PORT,
        "debug": False,
        "default_language": DEFAULT_LANGUAGE
    },
    "features": {
        "live_status": True,
        "ping_stats": True,
        "stats_retention_days": STATS_RETENTION_DAYS
    },
    "smtp": {
        "enabled": False,
        "server": "",
        "port": DEFAULT_SMTP_PORT,
        "username": "",
        "password": "",
        "use_tls": True,
        "from_address": "",
        "to_addresses": [],
        "notify_on_reset": True,
        "notify_on_error": True
    },
    "log_max_kb": DEFAULT_LOG_SIZE_KB,
    "log_view_lines": DEFAULT_LOG_VIEW_LINES
}

# Default admin user
DEFAULT_ADMIN = {
    "username": "admin",
    "role": ROLE_ADMIN,
    "language": DEFAULT_LANGUAGE,
    "created_at": None,  # Set on creation
    "last_login": None,
    "active": True
}

"""
Watchdog v4.2 - Internationalization (i18n)
==========================================
Multi-language support for Czech and English.
"""

import json
import os
from typing import Dict, Optional
from functools import lru_cache

from constants import TRANSLATIONS_DIR, LANGUAGES, DEFAULT_LANGUAGE, VERSION, COPYRIGHT


class I18n:
    """Internationalization handler."""
    
    def __init__(self):
        self._translations: Dict[str, Dict] = {}
        self._current_lang = DEFAULT_LANGUAGE
        self._load_translations()
    
    def _load_translations(self):
        """Load all translation files."""
        for lang in LANGUAGES.keys():
            file_path = os.path.join(TRANSLATIONS_DIR, f"{lang}.json")
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self._translations[lang] = json.load(f)
                except:
                    self._translations[lang] = {}
            else:
                # Use built-in translations
                self._translations[lang] = BUILTIN_TRANSLATIONS.get(lang, {})
    
    def set_language(self, lang: str):
        """Set current language."""
        if lang in LANGUAGES:
            self._current_lang = lang
    
    def get_language(self) -> str:
        """Get current language."""
        return self._current_lang
    
    def t(self, key: str, lang: str = None, **kwargs) -> str:
        """
        Translate a key.
        
        Args:
            key: Translation key (dot notation: "nav.dashboard")
            lang: Language override
            **kwargs: Interpolation variables
        
        Returns:
            Translated string or key if not found
        """
        lang = lang or self._current_lang
        translations = self._translations.get(lang, {})
        
        # Navigate nested keys
        value = translations
        for part in key.split('.'):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        
        # Fallback to English, then to key itself
        if value is None and lang != 'en':
            return self.t(key, 'en', **kwargs)
        
        if value is None:
            return key
        
        # Interpolate variables
        if kwargs:
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        
        return value
    
    def get_all(self, lang: str = None) -> Dict:
        """Get all translations for a language."""
        lang = lang or self._current_lang
        return self._translations.get(lang, {})


# Built-in translations (used when no external file exists)
# Note: version and copyright are dynamically injected from constants
BUILTIN_TRANSLATIONS = {
    "cs": {
        "app": {
            "name": "Watchdog",
            "version": f"v{VERSION}",
            "copyright": COPYRIGHT
        },
        "nav": {
            "dashboard": "Dashboard",
            "groups": "Skupiny serverů",
            "network": "Síť",
            "system": "Systém",
            "email": "Email",
            "scheduler": "Plánovač",
            "logs": "Logy",
            "audit": "Audit",
            "stats": "Statistiky",
            "users": "Uživatelé",
            "backups": "Zálohy",
            "account": "Můj účet",
            "logout": "Odhlásit"
        },
        "auth": {
            "login": "Přihlášení",
            "username": "Uživatelské jméno",
            "password": "Heslo",
            "login_btn": "Přihlásit se",
            "logout_btn": "Odhlásit",
            "invalid_credentials": "Neplatné přihlašovací údaje",
            "account_disabled": "Účet je deaktivován",
            "session_expired": "Relace vypršela, přihlaste se znovu"
        },
        "dashboard": {
            "title": "Dashboard",
            "active_groups": "Aktivní skupiny",
            "no_groups": "Žádné aktivní skupiny",
            "configure_groups": "Přejít na konfiguraci skupin",
            "system_info": "Systémové informace",
            "hostname": "Hostname",
            "check_interval": "Interval kontroly",
            "debug_mode": "Debug mód",
            "last_check": "Poslední kontrola",
            "uptime": "Uptime"
        },
        "groups": {
            "title": "Skupiny serverů",
            "add_group": "Přidat skupinu",
            "remove_group": "Odebrat",
            "group_name": "Název skupiny",
            "servers": "Servery",
            "servers_help": "IP adresy nebo hostname oddělené mezerou",
            "outlet": "Zásuvka (GPIO)",
            "fail_count": "Počet pokusů",
            "fail_count_help": "Kolikrát musí selhat ping před resetem",
            "off_time": "Doba výpadku",
            "off_time_help": "Jak dlouho bude napájení vypnuté (sekundy)",
            "enabled": "Aktivní monitoring",
            "save": "Uložit změny",
            "saved": "Skupiny uloženy"
        },
        "scheduler": {
            "title": "Plánované restarty",
            "enabled": "Povolit plánovaný restart",
            "day": "Den",
            "time": "Čas",
            "add_schedule": "Přidat plán",
            "no_schedules": "Žádné plánované restarty",
            "next_run": "Další spuštění"
        },
        "control": {
            "on": "ZAPNOUT",
            "off": "VYPNOUT",
            "restart": "RESTART",
            "confirm_restart": "Opravdu provést restart skupiny {group}?",
            "command_queued": "Příkaz zařazen do fronty",
            "command_error": "Chyba při provádění příkazu"
        },
        "users": {
            "title": "Správa uživatelů",
            "add_user": "Přidat uživatele",
            "edit_user": "Upravit uživatele",
            "delete_user": "Smazat uživatele",
            "username": "Uživatelské jméno",
            "role": "Role",
            "language": "Jazyk",
            "active": "Aktivní",
            "created": "Vytvořen",
            "last_login": "Poslední přihlášení",
            "never": "Nikdy",
            "reset_password": "Reset hesla",
            "new_password": "Nové heslo",
            "confirm_delete": "Opravdu smazat uživatele {user}?",
            "cannot_delete_self": "Nemůžete smazat sami sebe",
            "cannot_delete_last_admin": "Nelze smazat posledního administrátora"
        },
        "account": {
            "title": "Můj účet",
            "change_password": "Změna hesla",
            "current_password": "Aktuální heslo",
            "new_password": "Nové heslo",
            "confirm_password": "Potvrzení hesla",
            "passwords_mismatch": "Hesla se neshodují",
            "password_changed": "Heslo změněno",
            "language_preference": "Preferovaný jazyk",
            "api_token": "API Token",
            "generate_token": "Vygenerovat token",
            "revoke_token": "Zrušit token",
            "token_warning": "Token zobrazíte pouze jednou!"
        },
        "logs": {
            "title": "Systémové logy",
            "refresh": "Obnovit",
            "newer": "Novější",
            "older": "Starší",
            "page": "Stránka",
            "of": "z",
            "no_logs": "Žádné logy k zobrazení",
            "legend": "Legenda"
        },
        "audit": {
            "title": "Audit log",
            "event": "Událost",
            "user": "Uživatel",
            "ip": "IP adresa",
            "target": "Cíl",
            "details": "Detaily",
            "time": "Čas",
            "filter": "Filtrovat",
            "all_events": "Všechny události"
        },
        "stats": {
            "title": "Statistiky",
            "ping_history": "Historie ping",
            "response_time": "Doba odezvy",
            "availability": "Dostupnost",
            "avg_response": "Průměrná odezva",
            "uptime_percent": "Uptime",
            "total_resets": "Celkem resetů",
            "last_24h": "Posledních 24 hodin",
            "last_7d": "Posledních 7 dní",
            "last_30d": "Posledních 30 dní"
        },
        "network": {
            "title": "Síťová konfigurace",
            "mode": "Režim",
            "dhcp": "DHCP (automatická konfigurace)",
            "static": "Statická IP",
            "ip_address": "IP adresa",
            "netmask": "Maska sítě",
            "gateway": "Výchozí brána",
            "dns_servers": "DNS servery",
            "dns_help": "IP adresy DNS serverů oddělené mezerou",
            "saved": "Síťová konfigurace uložena"
        },
        "system": {
            "title": "Systémová konfigurace",
            "basic": "Základní nastavení",
            "hostname": "Hostname",
            "web_port": "Web port",
            "check_interval": "Interval kontroly",
            "debug_mode": "Debug mód",
            "ntp_servers": "NTP servery",
            "logging": "Logging",
            "log_max_size": "Maximální velikost logu",
            "log_lines": "Řádků na stránku",
            "features": "Funkce",
            "live_status": "Live status (AJAX)",
            "ping_stats": "Ukládání ping statistik",
            "ssl": "SSL/HTTPS",
            "ssl_enabled": "Povolit HTTPS",
            "ssl_port": "HTTPS port",
            "export_import": "Export / Import",
            "export": "Exportovat konfiguraci",
            "import": "Importovat konfiguraci",
            "saved": "Systémová konfigurace uložena"
        },
        "smtp": {
            "title": "Email notifikace",
            "enabled": "Povolit emailové notifikace",
            "server": "SMTP Server",
            "port": "Port",
            "username": "Uživatelské jméno",
            "password": "Heslo",
            "tls": "Použít TLS/STARTTLS",
            "from": "Odesílatel (From)",
            "to": "Příjemci (To)",
            "to_help": "Adresy oddělené čárkou nebo mezerou",
            "notifications": "Kdy notifikovat",
            "on_reset": "Při power resetu",
            "on_error": "Při chybách systému",
            "test": "Test připojení",
            "test_success": "Test úspěšný, email odeslán",
            "test_failed": "Test selhal",
            "saved": "SMTP konfigurace uložena"
        },
        "backups": {
            "title": "Zálohy konfigurace",
            "description": "Zálohy jsou automaticky vytvářeny při každé změně.",
            "file": "Soubor",
            "date": "Datum",
            "size": "Velikost",
            "restore": "Obnovit",
            "confirm_restore": "Opravdu obnovit tuto zálohu?",
            "no_backups": "Žádné zálohy k dispozici",
            "restored": "Konfigurace obnovena ze zálohy"
        },
        "common": {
            "save": "Uložit",
            "cancel": "Zrušit",
            "delete": "Smazat",
            "edit": "Upravit",
            "add": "Přidat",
            "yes": "Ano",
            "no": "Ne",
            "enabled": "Povoleno",
            "disabled": "Zakázáno",
            "active": "Aktivní",
            "inactive": "Neaktivní",
            "online": "Online",
            "offline": "Offline",
            "error": "Chyba",
            "success": "Úspěch",
            "warning": "Varování",
            "info": "Informace",
            "loading": "Načítání...",
            "seconds": "sekund",
            "minutes": "minut",
            "hours": "hodin",
            "days": "dní"
        },
        "roles": {
            "admin": "Administrátor",
            "operator": "Operátor",
            "viewer": "Pozorovatel"
        },
        "errors": {
            "not_found": "Stránka nenalezena",
            "forbidden": "Přístup odepřen",
            "server_error": "Interní chyba serveru",
            "invalid_request": "Neplatný požadavek",
            "session_expired": "Relace vypršela"
        }
    },
    "en": {
        "app": {
            "name": "Watchdog",
            "version": f"v{VERSION}",
            "copyright": COPYRIGHT
        },
        "nav": {
            "dashboard": "Dashboard",
            "groups": "Server Groups",
            "network": "Network",
            "system": "System",
            "email": "Email",
            "scheduler": "Scheduler",
            "logs": "Logs",
            "audit": "Audit",
            "stats": "Statistics",
            "users": "Users",
            "backups": "Backups",
            "account": "My Account",
            "logout": "Logout"
        },
        "auth": {
            "login": "Login",
            "username": "Username",
            "password": "Password",
            "login_btn": "Sign In",
            "logout_btn": "Sign Out",
            "invalid_credentials": "Invalid credentials",
            "account_disabled": "Account is disabled",
            "session_expired": "Session expired, please sign in again"
        },
        "dashboard": {
            "title": "Dashboard",
            "active_groups": "Active Groups",
            "no_groups": "No active groups",
            "configure_groups": "Go to group configuration",
            "system_info": "System Information",
            "hostname": "Hostname",
            "check_interval": "Check interval",
            "debug_mode": "Debug mode",
            "last_check": "Last check",
            "uptime": "Uptime"
        },
        "groups": {
            "title": "Server Groups",
            "add_group": "Add Group",
            "remove_group": "Remove",
            "group_name": "Group Name",
            "servers": "Servers",
            "servers_help": "IP addresses or hostnames separated by space",
            "outlet": "Outlet (GPIO)",
            "fail_count": "Fail Count",
            "fail_count_help": "How many pings must fail before reset",
            "off_time": "Off Time",
            "off_time_help": "How long power will be off (seconds)",
            "enabled": "Active monitoring",
            "save": "Save Changes",
            "saved": "Groups saved"
        },
        "scheduler": {
            "title": "Scheduled Restarts",
            "enabled": "Enable scheduled restart",
            "day": "Day",
            "time": "Time",
            "add_schedule": "Add Schedule",
            "no_schedules": "No scheduled restarts",
            "next_run": "Next run"
        },
        "control": {
            "on": "ON",
            "off": "OFF",
            "restart": "RESTART",
            "confirm_restart": "Really restart group {group}?",
            "command_queued": "Command queued",
            "command_error": "Command execution error"
        },
        "users": {
            "title": "User Management",
            "add_user": "Add User",
            "edit_user": "Edit User",
            "delete_user": "Delete User",
            "username": "Username",
            "role": "Role",
            "language": "Language",
            "active": "Active",
            "created": "Created",
            "last_login": "Last Login",
            "never": "Never",
            "reset_password": "Reset Password",
            "new_password": "New Password",
            "confirm_delete": "Really delete user {user}?",
            "cannot_delete_self": "Cannot delete yourself",
            "cannot_delete_last_admin": "Cannot delete last administrator"
        },
        "account": {
            "title": "My Account",
            "change_password": "Change Password",
            "current_password": "Current Password",
            "new_password": "New Password",
            "confirm_password": "Confirm Password",
            "passwords_mismatch": "Passwords do not match",
            "password_changed": "Password changed",
            "language_preference": "Preferred Language",
            "api_token": "API Token",
            "generate_token": "Generate Token",
            "revoke_token": "Revoke Token",
            "token_warning": "Token is shown only once!"
        },
        "logs": {
            "title": "System Logs",
            "refresh": "Refresh",
            "newer": "Newer",
            "older": "Older",
            "page": "Page",
            "of": "of",
            "no_logs": "No logs to display",
            "legend": "Legend"
        },
        "audit": {
            "title": "Audit Log",
            "event": "Event",
            "user": "User",
            "ip": "IP Address",
            "target": "Target",
            "details": "Details",
            "time": "Time",
            "filter": "Filter",
            "all_events": "All events"
        },
        "stats": {
            "title": "Statistics",
            "ping_history": "Ping History",
            "response_time": "Response Time",
            "availability": "Availability",
            "avg_response": "Average Response",
            "uptime_percent": "Uptime",
            "total_resets": "Total Resets",
            "last_24h": "Last 24 hours",
            "last_7d": "Last 7 days",
            "last_30d": "Last 30 days"
        },
        "network": {
            "title": "Network Configuration",
            "mode": "Mode",
            "dhcp": "DHCP (automatic)",
            "static": "Static IP",
            "ip_address": "IP Address",
            "netmask": "Netmask",
            "gateway": "Gateway",
            "dns_servers": "DNS Servers",
            "dns_help": "DNS server IPs separated by space",
            "saved": "Network configuration saved"
        },
        "system": {
            "title": "System Configuration",
            "basic": "Basic Settings",
            "hostname": "Hostname",
            "web_port": "Web Port",
            "check_interval": "Check Interval",
            "debug_mode": "Debug Mode",
            "ntp_servers": "NTP Servers",
            "logging": "Logging",
            "log_max_size": "Max Log Size",
            "log_lines": "Lines per Page",
            "features": "Features",
            "live_status": "Live Status (AJAX)",
            "ping_stats": "Save Ping Statistics",
            "ssl": "SSL/HTTPS",
            "ssl_enabled": "Enable HTTPS",
            "ssl_port": "HTTPS Port",
            "export_import": "Export / Import",
            "export": "Export Configuration",
            "import": "Import Configuration",
            "saved": "System configuration saved"
        },
        "smtp": {
            "title": "Email Notifications",
            "enabled": "Enable email notifications",
            "server": "SMTP Server",
            "port": "Port",
            "username": "Username",
            "password": "Password",
            "tls": "Use TLS/STARTTLS",
            "from": "From Address",
            "to": "To Addresses",
            "to_help": "Addresses separated by comma or space",
            "notifications": "When to notify",
            "on_reset": "On power reset",
            "on_error": "On system errors",
            "test": "Test Connection",
            "test_success": "Test successful, email sent",
            "test_failed": "Test failed",
            "saved": "SMTP configuration saved"
        },
        "backups": {
            "title": "Configuration Backups",
            "description": "Backups are created automatically on each change.",
            "file": "File",
            "date": "Date",
            "size": "Size",
            "restore": "Restore",
            "confirm_restore": "Really restore this backup?",
            "no_backups": "No backups available",
            "restored": "Configuration restored from backup"
        },
        "common": {
            "save": "Save",
            "cancel": "Cancel",
            "delete": "Delete",
            "edit": "Edit",
            "add": "Add",
            "yes": "Yes",
            "no": "No",
            "enabled": "Enabled",
            "disabled": "Disabled",
            "active": "Active",
            "inactive": "Inactive",
            "online": "Online",
            "offline": "Offline",
            "error": "Error",
            "success": "Success",
            "warning": "Warning",
            "info": "Info",
            "loading": "Loading...",
            "seconds": "seconds",
            "minutes": "minutes",
            "hours": "hours",
            "days": "days"
        },
        "roles": {
            "admin": "Administrator",
            "operator": "Operator",
            "viewer": "Viewer"
        },
        "errors": {
            "not_found": "Page not found",
            "forbidden": "Access denied",
            "server_error": "Internal server error",
            "invalid_request": "Invalid request",
            "session_expired": "Session expired"
        }
    }
}


# Global instance
i18n = I18n()


def t(key: str, **kwargs) -> str:
    """Shortcut for translation."""
    return i18n.t(key, **kwargs)


def set_language(lang: str):
    """Set current language."""
    i18n.set_language(lang)


def get_language() -> str:
    """Get current language."""
    return i18n.get_language()

"""
Watchdog v4.0 - Audit Log
=========================
Track all security-relevant events.
"""

import os
import json
import fcntl
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from constants import (
    AUDIT_FILE, LOG_DIR,
    AUDIT_LOGIN, AUDIT_LOGOUT, AUDIT_LOGIN_FAILED,
    AUDIT_CONFIG_CHANGE, AUDIT_USER_CHANGE, AUDIT_RELAY_CONTROL,
    AUDIT_SCHEDULED_RESTART, AUDIT_AUTO_RESTART, AUDIT_PASSWORD_CHANGE
)


class AuditLogger:
    """Thread-safe audit logger."""
    
    EVENT_ICONS = {
        AUDIT_LOGIN: "🔓",
        AUDIT_LOGOUT: "🔒",
        AUDIT_LOGIN_FAILED: "⛔",
        AUDIT_CONFIG_CHANGE: "⚙️",
        AUDIT_USER_CHANGE: "👤",
        AUDIT_RELAY_CONTROL: "⚡",
        AUDIT_SCHEDULED_RESTART: "📅",
        AUDIT_AUTO_RESTART: "🔄",
        AUDIT_PASSWORD_CHANGE: "🔑"
    }
    
    EVENT_NAMES = {
        AUDIT_LOGIN: {"en": "Login", "cs": "Přihlášení"},
        AUDIT_LOGOUT: {"en": "Logout", "cs": "Odhlášení"},
        AUDIT_LOGIN_FAILED: {"en": "Login Failed", "cs": "Neúspěšné přihlášení"},
        AUDIT_CONFIG_CHANGE: {"en": "Config Change", "cs": "Změna konfigurace"},
        AUDIT_USER_CHANGE: {"en": "User Change", "cs": "Změna uživatele"},
        AUDIT_RELAY_CONTROL: {"en": "Relay Control", "cs": "Ovládání relé"},
        AUDIT_SCHEDULED_RESTART: {"en": "Scheduled Restart", "cs": "Plánovaný restart"},
        AUDIT_AUTO_RESTART: {"en": "Auto Restart", "cs": "Automatický restart"},
        AUDIT_PASSWORD_CHANGE: {"en": "Password Change", "cs": "Změna hesla"}
    }
    
    def __init__(self, log_file: str = AUDIT_FILE):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    def log(self, event_type: str, username: str, details: str = "",
            ip_address: str = "", target: str = ""):
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (AUDIT_* constant)
            username: User who performed the action
            details: Additional details
            ip_address: Client IP address
            target: Target of the action (e.g., affected user, group name)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "user": username,
            "ip": ip_address,
            "target": target,
            "details": details
        }
        
        # Append to log file (thread-safe)
        try:
            with open(self.log_file, "a") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.write(json.dumps(entry) + "\n")
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            print(f"Audit log error: {e}")
    
    def get_entries(self, limit: int = 100, event_type: str = None,
                    username: str = None, since: datetime = None,
                    until: datetime = None) -> List[Dict]:
        """
        Get audit entries with optional filtering.
        
        Args:
            limit: Max entries to return
            event_type: Filter by event type
            username: Filter by username
            since: Filter entries after this time
            until: Filter entries before this time
        """
        entries = []
        
        if not os.path.exists(self.log_file):
            return entries
        
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        
                        # Apply filters
                        if event_type and entry.get("event") != event_type:
                            continue
                        
                        if username and entry.get("user") != username:
                            continue
                        
                        entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
                        
                        if since and entry_time < since:
                            continue
                        
                        if until and entry_time > until:
                            continue
                        
                        entries.append(entry)
                        
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            # Return newest first, limited
            entries.reverse()
            return entries[:limit]
            
        except Exception as e:
            print(f"Audit read error: {e}")
            return []
    
    def get_formatted_entries(self, limit: int = 100, language: str = "cs", **filters) -> List[Dict]:
        """Get entries with formatted display data."""
        entries = self.get_entries(limit, **filters)
        
        formatted = []
        for entry in entries:
            event_type = entry.get("event", "")
            formatted.append({
                **entry,
                "icon": self.EVENT_ICONS.get(event_type, "📝"),
                "event_name": self.EVENT_NAMES.get(event_type, {}).get(language, event_type),
                "formatted_time": self._format_time(entry.get("timestamp"), language)
            })
        
        return formatted
    
    def _format_time(self, timestamp: str, language: str) -> str:
        """Format timestamp for display."""
        try:
            dt = datetime.fromisoformat(timestamp)
            if language == "cs":
                return dt.strftime("%d.%m.%Y %H:%M:%S")
            else:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return timestamp
    
    def cleanup(self, days: int = 90):
        """Remove entries older than specified days."""
        if not os.path.exists(self.log_file):
            return
        
        cutoff = datetime.now() - timedelta(days=days)
        
        try:
            # Read all entries
            with open(self.log_file, "r") as f:
                lines = f.readlines()
            
            # Filter to keep only recent
            kept = []
            for line in lines:
                try:
                    entry = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
                    if entry_time >= cutoff:
                        kept.append(line)
                except:
                    pass
            
            # Write back
            with open(self.log_file, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.writelines(kept)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                
        except Exception as e:
            print(f"Audit cleanup error: {e}")
    
    # Convenience methods
    def log_login(self, username: str, ip: str):
        self.log(AUDIT_LOGIN, username, ip_address=ip)
    
    def log_logout(self, username: str, ip: str):
        self.log(AUDIT_LOGOUT, username, ip_address=ip)
    
    def log_login_failed(self, username: str, ip: str):
        self.log(AUDIT_LOGIN_FAILED, username, ip_address=ip)
    
    def log_config_change(self, username: str, section: str, details: str = "", ip: str = ""):
        self.log(AUDIT_CONFIG_CHANGE, username, details=details, target=section, ip_address=ip)
    
    def log_user_change(self, admin: str, target_user: str, action: str, ip: str = ""):
        self.log(AUDIT_USER_CHANGE, admin, details=action, target=target_user, ip_address=ip)
    
    def log_relay_control(self, username: str, group: str, action: str, ip: str = ""):
        self.log(AUDIT_RELAY_CONTROL, username, details=action, target=group, ip_address=ip)
    
    def log_scheduled_restart(self, group: str):
        self.log(AUDIT_SCHEDULED_RESTART, "scheduler", target=group, details="Scheduled restart executed")
    
    def log_auto_restart(self, group: str, servers: List[str]):
        self.log(AUDIT_AUTO_RESTART, "watchdog", target=group, 
                details=f"Servers unreachable: {', '.join(servers)}")
    
    def log_password_change(self, username: str, target_user: str = None, ip: str = ""):
        target = target_user or username
        action = "Password changed" if target == username else "Password reset by admin"
        self.log(AUDIT_PASSWORD_CHANGE, username, details=action, target=target, ip_address=ip)


# Global instance
audit_log = AuditLogger()

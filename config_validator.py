"""
Watchdog v4.0 - Configuration Validator & Migrator
===================================================
Validates, repairs, and migrates configuration between versions.
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

from constants import (
    CONFIG_FILE, BACKUP_DIR, VERSION, DEFAULT_CONFIG,
    MAX_GROUPS, MIN_FAIL_COUNT, MAX_FAIL_COUNT,
    MIN_OFF_TIME, MAX_OFF_TIME, MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL,
    DEFAULT_LOG_SIZE_KB, DEFAULT_LOG_VIEW_LINES, DEFAULT_LANGUAGE,
    VALID_GPIO_PINS, DEFAULT_TIMEZONE
)


class ConfigError(Exception):
    """Configuration error with details."""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


class ConfigMigrator:
    """Handles config migration between versions."""
    
    @classmethod
    def get_version(cls, config: dict) -> str:
        """Get config version."""
        return config.get("version", "3.0.0")
    
    @classmethod
    def needs_migration(cls, config: dict) -> bool:
        """Check if config needs migration."""
        current = cls.get_version(config)
        return current != VERSION
    
    @classmethod
    def migrate(cls, config: dict) -> Tuple[dict, List[str]]:
        """
        Migrate config to current version.
        Returns (migrated_config, list_of_changes).
        """
        changes = []
        current_version = cls.get_version(config)
        
        # v3.x -> v4.0
        if current_version.startswith("3.") or current_version < "4.0.0":
            config, v3_changes = cls._migrate_v3_to_v4(config)
            changes.extend(v3_changes)
        
        # v4.0.x -> v4.1
        if current_version.startswith("4.0"):
            config, v41_changes = cls._migrate_v40_to_v41(config)
            changes.extend(v41_changes)
        
        # v4.1.x -> v4.2 (no config changes, just version bump)
        
        # Update version
        if config.get("version") != VERSION:
            config["version"] = VERSION
            changes.append(f"Updated version to {VERSION}")
        
        return config, changes
    
    @classmethod
    def _migrate_v40_to_v41(cls, config: dict) -> Tuple[dict, List[str]]:
        """Migrate from v4.0.x to v4.1."""
        changes = []
        
        # Add timezone if missing
        if "system" in config:
            if "timezone" not in config["system"]:
                config["system"]["timezone"] = DEFAULT_TIMEZONE
                changes.append(f"Added timezone: {DEFAULT_TIMEZONE}")
        
        return config, changes
    
    @classmethod
    def _migrate_v3_to_v4(cls, config: dict) -> Tuple[dict, List[str]]:
        """Migrate from v3.x to v4.0."""
        changes = []
        
        # Add features section
        if "features" not in config:
            config["features"] = {
                "live_status": True,
                "ping_stats": True,
                "stats_retention_days": 30
            }
            changes.append("Added 'features' section (live_status, ping_stats)")
        
        # Add SSL settings to system
        if "system" not in config:
            config["system"] = {}
        
        if "ssl_enabled" not in config["system"]:
            config["system"]["ssl_enabled"] = False
            config["system"]["ssl_port"] = 443
            changes.append("Added SSL configuration (disabled by default)")
        
        if "default_language" not in config["system"]:
            config["system"]["default_language"] = DEFAULT_LANGUAGE
            changes.append(f"Added default_language: {DEFAULT_LANGUAGE}")
        
        # Add schedules to groups
        for i, group in enumerate(config.get("groups", [])):
            if "schedules" not in group:
                group["schedules"] = []
                changes.append(f"Added schedules array to group '{group.get('name', i)}'")
        
        # Extend outlets from 4 to 8 (if user had only 4)
        if "outlets" in config:
            existing_outlets = len(config["outlets"])
            if existing_outlets < 8:
                # Add additional outlets with default GPIO pins
                new_outlet_pins = {
                    5: 23, 6: 24, 7: 25, 8: 5,  # outlet_5 through outlet_8
                    9: 6, 10: 12, 11: 13, 12: 16,
                    13: 19, 14: 20, 15: 21, 16: 26
                }
                # Get already used pins
                used_pins = set()
                for outlet in config["outlets"].values():
                    used_pins.add(outlet.get("gpio_pin"))
                
                # Add outlets up to 8
                for num in range(existing_outlets + 1, 9):
                    key = f"outlet_{num}"
                    if key not in config["outlets"]:
                        # Find unused pin
                        pin = new_outlet_pins.get(num, 4)
                        while pin in used_pins and pin < 28:
                            pin += 1
                        if pin not in used_pins:
                            config["outlets"][key] = {
                                "name": f"Zásuvka {num}",
                                "gpio_pin": pin
                            }
                            used_pins.add(pin)
                            changes.append(f"Added outlet_{num} (GPIO {pin})")
        
        # Ensure SMTP has all fields
        if "smtp" not in config:
            config["smtp"] = {}
        
        smtp_defaults = {
            "enabled": False,
            "server": "",
            "port": 587,
            "username": "",
            "password": "",
            "use_tls": True,
            "from_address": "",
            "to_addresses": [],
            "notify_on_reset": True,
            "notify_on_error": True
        }
        for key, default in smtp_defaults.items():
            if key not in config["smtp"]:
                config["smtp"][key] = default
                changes.append(f"Added smtp.{key}")
        
        # Ensure network section
        if "network" not in config:
            config["network"] = {
                "mode": "dhcp",
                "static_ip": "",
                "netmask": "255.255.255.0",
                "gateway": "",
                "dns_servers": ["8.8.8.8", "1.1.1.1"]
            }
            changes.append("Added network section")
        
        return config, changes


class ConfigValidator:
    """Validates and repairs configuration."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self, config: dict) -> Tuple[bool, List[str]]:
        """
        Validate configuration structure and values.
        Returns (is_valid, list_of_errors).
        """
        self.errors = []
        self.warnings = []
        
        if not isinstance(config, dict):
            return False, ["Configuration must be a dictionary"]
        
        # Required sections
        required = ["outlets", "groups"]
        for section in required:
            if section not in config:
                self.errors.append(f"Missing required section: {section}")
        
        # Validate outlets
        if "outlets" in config:
            self._validate_outlets(config["outlets"])
        
        # Validate groups
        if "groups" in config:
            self._validate_groups(config["groups"], config.get("outlets", {}))
        
        # Validate intervals
        if "check_interval" in config:
            interval = config["check_interval"]
            if not isinstance(interval, int) or interval < MIN_CHECK_INTERVAL or interval > MAX_CHECK_INTERVAL:
                self.errors.append(f"check_interval must be {MIN_CHECK_INTERVAL}-{MAX_CHECK_INTERVAL}")
        
        # Validate SMTP if present
        if "smtp" in config and config["smtp"].get("enabled"):
            self._validate_smtp(config["smtp"])
        
        return len(self.errors) == 0, self.errors
    
    def _validate_outlets(self, outlets: dict):
        """Validate outlets configuration."""
        if not isinstance(outlets, dict):
            self.errors.append("outlets must be a dictionary")
            return
        
        used_pins = set()
        for key, outlet in outlets.items():
            if not isinstance(outlet, dict):
                self.errors.append(f"Outlet {key} must be a dictionary")
                continue
            
            pin = outlet.get("gpio_pin")
            if pin is None:
                self.errors.append(f"Outlet {key} missing gpio_pin")
            elif pin not in VALID_GPIO_PINS:
                self.warnings.append(f"Outlet {key} uses non-standard GPIO pin {pin}")
            elif pin in used_pins:
                self.errors.append(f"Outlet {key} uses duplicate GPIO pin {pin}")
            else:
                used_pins.add(pin)
    
    def _validate_groups(self, groups: list, outlets: dict):
        """Validate server groups."""
        if not isinstance(groups, list):
            self.errors.append("groups must be a list")
            return
        
        if len(groups) > MAX_GROUPS:
            self.warnings.append(f"More than {MAX_GROUPS} groups defined")
        
        for i, group in enumerate(groups):
            if not isinstance(group, dict):
                self.errors.append(f"Group {i} must be a dictionary")
                continue
            
            # Check required fields
            if not group.get("name"):
                self.errors.append(f"Group {i} missing name")
            
            if not group.get("servers"):
                self.warnings.append(f"Group '{group.get('name', i)}' has no servers")
            
            # Check outlet reference
            outlet_key = group.get("outlet")
            if outlet_key and outlet_key not in outlets:
                self.errors.append(f"Group '{group.get('name', i)}' references unknown outlet: {outlet_key}")
            
            # Check numeric ranges
            fail_count = group.get("fail_count", 3)
            if not isinstance(fail_count, int) or fail_count < MIN_FAIL_COUNT or fail_count > MAX_FAIL_COUNT:
                self.warnings.append(f"Group '{group.get('name', i)}' fail_count out of range, will be clamped")
            
            off_time = group.get("off_time", 10)
            if not isinstance(off_time, int) or off_time < MIN_OFF_TIME or off_time > MAX_OFF_TIME:
                self.warnings.append(f"Group '{group.get('name', i)}' off_time out of range, will be clamped")
            
            # Validate schedules if present
            for j, schedule in enumerate(group.get("schedules", [])):
                if not isinstance(schedule, dict):
                    self.errors.append(f"Group '{group.get('name', i)}' schedule {j} must be a dictionary")
                    continue
                
                day = schedule.get("day", 0)
                if not isinstance(day, int) or day < 0 or day > 6:
                    self.errors.append(f"Group '{group.get('name', i)}' schedule {j} has invalid day")
                
                hour = schedule.get("hour", 0)
                if not isinstance(hour, int) or hour < 0 or hour > 23:
                    self.errors.append(f"Group '{group.get('name', i)}' schedule {j} has invalid hour")
                
                minute = schedule.get("minute", 0)
                if not isinstance(minute, int) or minute < 0 or minute > 59:
                    self.errors.append(f"Group '{group.get('name', i)}' schedule {j} has invalid minute")
    
    def _validate_smtp(self, smtp: dict):
        """Validate SMTP configuration."""
        if not smtp.get("server"):
            self.errors.append("SMTP enabled but no server specified")
        
        if not smtp.get("from_address"):
            self.warnings.append("SMTP enabled but no from_address specified")
        
        if not smtp.get("to_addresses"):
            self.warnings.append("SMTP enabled but no recipients specified")
    
    def repair(self, config: dict) -> dict:
        """
        Repair configuration by merging with defaults and clamping values.
        """
        # Start with defaults and merge user config
        repaired = self._deep_merge(DEFAULT_CONFIG.copy(), config)
        
        # Clamp numeric values
        repaired["check_interval"] = max(MIN_CHECK_INTERVAL, 
                                         min(MAX_CHECK_INTERVAL, 
                                             repaired.get("check_interval", 10)))
        
        repaired["log_max_kb"] = max(64, min(4096, repaired.get("log_max_kb", DEFAULT_LOG_SIZE_KB)))
        repaired["log_view_lines"] = max(10, min(500, repaired.get("log_view_lines", DEFAULT_LOG_VIEW_LINES)))
        
        # Repair groups
        for group in repaired.get("groups", []):
            group["fail_count"] = max(MIN_FAIL_COUNT, 
                                      min(MAX_FAIL_COUNT, 
                                          group.get("fail_count", 3)))
            group["off_time"] = max(MIN_OFF_TIME, 
                                    min(MAX_OFF_TIME, 
                                        group.get("off_time", 10)))
            
            # Ensure schedules exists
            if "schedules" not in group:
                group["schedules"] = []
        
        return repaired
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def backup(self, config_path: str = CONFIG_FILE) -> Optional[str]:
        """Create backup of current config."""
        if not os.path.exists(config_path):
            return None
        
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"config_{timestamp}.json")
        
        shutil.copy2(config_path, backup_path)
        
        # Keep only last 20 backups
        self._cleanup_backups()
        
        return backup_path
    
    def _cleanup_backups(self, keep: int = 20):
        """Remove old backups, keeping the most recent ones."""
        if not os.path.exists(BACKUP_DIR):
            return
        
        backups = sorted([
            os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR)
            if f.startswith("config_") and f.endswith(".json")
        ], key=os.path.getmtime, reverse=True)
        
        for old_backup in backups[keep:]:
            try:
                os.remove(old_backup)
            except:
                pass
    
    def get_backups(self) -> List[str]:
        """Get list of available backups."""
        if not os.path.exists(BACKUP_DIR):
            return []
        
        return sorted([
            os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR)
            if f.startswith("config_") and f.endswith(".json")
        ], key=os.path.getmtime, reverse=True)
    
    def restore(self, backup_path: str) -> bool:
        """Restore configuration from backup."""
        if not os.path.exists(backup_path):
            return False
        
        try:
            # Validate backup before restoring
            with open(backup_path) as f:
                backup_config = json.load(f)
            
            valid, errors = self.validate(backup_config)
            if not valid:
                return False
            
            # Create backup of current before overwriting
            self.backup()
            
            # Copy backup to config
            shutil.copy2(backup_path, CONFIG_FILE)
            return True
            
        except Exception:
            return False


def load_config() -> dict:
    """
    Load and validate configuration.
    Automatically migrates older versions.
    """
    validator = ConfigValidator()
    
    if not os.path.exists(CONFIG_FILE):
        # Create default config
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON: {e}")
    
    # Check if migration needed
    if ConfigMigrator.needs_migration(config):
        # Backup before migration (ignore errors)
        try:
            validator.backup()
        except Exception:
            pass
        
        # Migrate
        config, changes = ConfigMigrator.migrate(config)
        
        # Log changes
        if changes:
            try:
                from logger import log
                log("CONFIG", f"Migrated config to v{VERSION}: {len(changes)} changes")
                for change in changes:
                    log("CONFIG", f"  - {change}")
            except:
                print(f"Migrated config: {len(changes)} changes")
        
        # Save migrated config
        save_config(config, backup=False)  # Already backed up
    
    # Validate
    valid, errors = validator.validate(config)
    
    if not valid:
        # Try to repair
        config = validator.repair(config)
        save_config(config, backup=True)
    
    return config


def save_config(config: dict, backup: bool = True):
    """Save configuration to file."""
    validator = ConfigValidator()
    
    # Backup current if requested (ignore errors)
    if backup and os.path.exists(CONFIG_FILE):
        try:
            validator.backup()
        except Exception:
            pass
    
    # Ensure version is set
    config["version"] = VERSION
    
    # Repair/validate before saving
    config = validator.repair(config)
    
    # Save
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_migration_status() -> dict:
    """Get info about config migration status."""
    if not os.path.exists(CONFIG_FILE):
        return {
            "exists": False,
            "version": None,
            "needs_migration": False,
            "target_version": VERSION
        }
    
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        
        current = ConfigMigrator.get_version(config)
        
        return {
            "exists": True,
            "version": current,
            "needs_migration": ConfigMigrator.needs_migration(config),
            "target_version": VERSION
        }
    except:
        return {
            "exists": True,
            "version": "unknown",
            "needs_migration": True,
            "target_version": VERSION
        }

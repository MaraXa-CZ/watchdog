"""
Watchdog v3.0 - Enhanced Logger
===============================
Thread-safe logging with rotation and notification hooks.
"""

import os
import json
import threading
from datetime import datetime
from typing import Optional, Callable, List

from constants import LOG_FILE, LOG_DIR, CONFIG_FILE, DEFAULT_LOG_SIZE_KB


class Logger:
    """Thread-safe logger with rotation."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._write_lock = threading.Lock()
        self._notification_hooks: List[Callable[[str, str], None]] = []
        
        # Ensure log directory exists
        os.makedirs(LOG_DIR, exist_ok=True)
    
    def log(self, level: str, message: str, notify: bool = False):
        """
        Write log entry.
        
        Args:
            level: Log level (INFO, ERROR, RESET, etc.)
            message: Log message
            notify: If True, trigger notification hooks
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {level:8s} | {message}\n"
        
        # Print to stdout
        print(entry.strip())
        
        # Write to file (thread-safe)
        with self._write_lock:
            try:
                # Check rotation before write
                self._check_rotation()
                
                with open(LOG_FILE, "a") as f:
                    f.write(entry)
            except Exception as e:
                print(f"[{timestamp}] ERROR    | Log write failed: {e}")
        
        # Trigger notification hooks
        if notify:
            self._trigger_hooks(level, message)
    
    def _check_rotation(self):
        """Rotate log if too large."""
        if not os.path.exists(LOG_FILE):
            return
        
        try:
            size_kb = os.path.getsize(LOG_FILE) / 1024
            max_kb = self._get_max_kb()
            
            if size_kb > max_kb:
                self._rotate()
        except:
            pass
    
    def _rotate(self):
        """Perform log rotation."""
        try:
            backup = LOG_FILE + ".old"
            if os.path.exists(backup):
                os.remove(backup)
            os.rename(LOG_FILE, backup)
            
            # Write rotation notice to new log
            with open(LOG_FILE, "w") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] INFO     | Log rotated\n")
        except Exception as e:
            print(f"Log rotation failed: {e}")
    
    def _get_max_kb(self) -> int:
        """Get max log size from config."""
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f).get("log_max_kb", DEFAULT_LOG_SIZE_KB)
        except:
            return DEFAULT_LOG_SIZE_KB
    
    def add_notification_hook(self, callback: Callable[[str, str], None]):
        """Add a callback for notifications (level, message)."""
        self._notification_hooks.append(callback)
    
    def _trigger_hooks(self, level: str, message: str):
        """Call all notification hooks."""
        for hook in self._notification_hooks:
            try:
                hook(level, message)
            except Exception as e:
                print(f"Notification hook error: {e}")
    
    def get_lines(self, n: int = 50, reverse: bool = True) -> List[str]:
        """
        Get log lines.
        
        Args:
            n: Number of lines
            reverse: If True, newest first
        """
        try:
            with open(LOG_FILE) as f:
                lines = f.readlines()
            
            if reverse:
                lines.reverse()
            
            return lines[:n]
        except:
            return []
    
    def get_page(self, page: int = 0, lines_per_page: int = 50) -> tuple:
        """
        Get paginated log lines.
        
        Returns: (lines, current_page, total_pages)
        """
        try:
            with open(LOG_FILE) as f:
                all_lines = f.readlines()
        except:
            return [], 0, 0
        
        # Newest first
        all_lines.reverse()
        
        total_lines = len(all_lines)
        total_pages = max(1, (total_lines + lines_per_page - 1) // lines_per_page)
        
        start = page * lines_per_page
        end = start + lines_per_page
        
        return all_lines[start:end], page, total_pages
    
    def clear(self, keep_last: int = 0):
        """Clear log file, optionally keeping last N lines."""
        with self._write_lock:
            try:
                if keep_last > 0:
                    with open(LOG_FILE) as f:
                        lines = f.readlines()
                    lines = lines[-keep_last:]
                else:
                    lines = []
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(LOG_FILE, "w") as f:
                    f.write(f"[{timestamp}] INFO     | Log cleared\n")
                    f.writelines(lines)
            except Exception as e:
                print(f"Log clear failed: {e}")


# Global logger instance
_logger = Logger()


def log(level: str, message: str, notify: bool = False):
    """Convenience function for logging."""
    _logger.log(level, message, notify)


def get_last_lines(n: int = 50) -> List[str]:
    """Get last N log lines."""
    return _logger.get_lines(n)


def get_log_page(page: int = 0, lines_per_page: int = 50) -> tuple:
    """Get paginated log."""
    return _logger.get_page(page, lines_per_page)


def add_notification_hook(callback: Callable[[str, str], None]):
    """Add notification callback."""
    _logger.add_notification_hook(callback)

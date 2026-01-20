"""
Watchdog v4.0 - Scheduler
=========================
Scheduled automatic restarts for server groups.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from constants import DAYS_OF_WEEK
from logger import log
from audit import audit_log


class ScheduleEntry:
    """Single schedule entry."""
    
    def __init__(self, day: int, hour: int, minute: int, enabled: bool = True):
        """
        Args:
            day: Day of week (0=Monday, 6=Sunday)
            hour: Hour (0-23)
            minute: Minute (0-59)
            enabled: Whether schedule is active
        """
        self.day = day
        self.hour = hour
        self.minute = minute
        self.enabled = enabled
        self.last_run: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "hour": self.hour,
            "minute": self.minute,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ScheduleEntry':
        entry = cls(
            day=data.get("day", 0),
            hour=data.get("hour", 0),
            minute=data.get("minute", 0),
            enabled=data.get("enabled", True)
        )
        if data.get("last_run"):
            try:
                entry.last_run = datetime.fromisoformat(data["last_run"])
            except:
                pass
        return entry
    
    def should_run(self, now: datetime = None) -> bool:
        """Check if this schedule should run now."""
        if not self.enabled:
            return False
        
        now = now or datetime.now()
        
        # Check day of week
        if now.weekday() != self.day:
            return False
        
        # Check time (within 1 minute window)
        if now.hour != self.hour or now.minute != self.minute:
            return False
        
        # Prevent running twice in same minute
        if self.last_run:
            if (now - self.last_run).total_seconds() < 120:
                return False
        
        return True
    
    def get_next_run(self) -> datetime:
        """Calculate next scheduled run time."""
        now = datetime.now()
        
        # Start from today at scheduled time
        next_run = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
        
        # Find next matching day
        days_ahead = self.day - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and next_run <= now):
            days_ahead += 7
        
        next_run += timedelta(days=days_ahead)
        return next_run
    
    def mark_run(self):
        """Mark this schedule as just run."""
        self.last_run = datetime.now()
    
    def get_day_name(self, language: str = "cs") -> str:
        """Get localized day name."""
        day_info = DAYS_OF_WEEK.get(self.day, {})
        return day_info.get(language, str(self.day))
    
    def get_time_str(self) -> str:
        """Get formatted time string."""
        return f"{self.hour:02d}:{self.minute:02d}"


class GroupScheduler:
    """Scheduler for a single group."""
    
    def __init__(self, group_name: str):
        self.group_name = group_name
        self.schedules: List[ScheduleEntry] = []
    
    def add_schedule(self, day: int, hour: int, minute: int, enabled: bool = True) -> bool:
        """Add a schedule entry."""
        # Check for duplicates
        for s in self.schedules:
            if s.day == day and s.hour == hour and s.minute == minute:
                return False
        
        self.schedules.append(ScheduleEntry(day, hour, minute, enabled))
        return True
    
    def remove_schedule(self, index: int) -> bool:
        """Remove schedule by index."""
        if 0 <= index < len(self.schedules):
            del self.schedules[index]
            return True
        return False
    
    def update_schedule(self, index: int, **kwargs) -> bool:
        """Update schedule entry."""
        if 0 <= index < len(self.schedules):
            schedule = self.schedules[index]
            if "day" in kwargs:
                schedule.day = kwargs["day"]
            if "hour" in kwargs:
                schedule.hour = kwargs["hour"]
            if "minute" in kwargs:
                schedule.minute = kwargs["minute"]
            if "enabled" in kwargs:
                schedule.enabled = kwargs["enabled"]
            return True
        return False
    
    def check_and_run(self, callback) -> bool:
        """
        Check if any schedule should run and execute callback.
        
        Args:
            callback: Function to call with group_name when schedule triggers
        
        Returns:
            True if a schedule was triggered
        """
        now = datetime.now()
        
        for schedule in self.schedules:
            if schedule.should_run(now):
                log("SCHEDULE", f"[{self.group_name}] Scheduled restart triggered")
                audit_log.log_scheduled_restart(self.group_name)
                schedule.mark_run()
                callback(self.group_name)
                return True
        
        return False
    
    def get_next_run(self) -> Optional[datetime]:
        """Get next scheduled run across all entries."""
        next_runs = []
        for schedule in self.schedules:
            if schedule.enabled:
                next_runs.append(schedule.get_next_run())
        
        return min(next_runs) if next_runs else None
    
    def to_dict(self) -> dict:
        return {
            "group_name": self.group_name,
            "schedules": [s.to_dict() for s in self.schedules]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GroupScheduler':
        scheduler = cls(data.get("group_name", ""))
        for s_data in data.get("schedules", []):
            scheduler.schedules.append(ScheduleEntry.from_dict(s_data))
        return scheduler


class Scheduler:
    """Main scheduler managing all groups."""
    
    def __init__(self):
        self._groups: Dict[str, GroupScheduler] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._restart_callback = None
        self._lock = threading.Lock()
    
    def set_restart_callback(self, callback):
        """Set callback function for triggering restarts."""
        self._restart_callback = callback
    
    def get_group(self, group_name: str) -> GroupScheduler:
        """Get or create group scheduler."""
        with self._lock:
            if group_name not in self._groups:
                self._groups[group_name] = GroupScheduler(group_name)
            return self._groups[group_name]
    
    def remove_group(self, group_name: str):
        """Remove group scheduler."""
        with self._lock:
            if group_name in self._groups:
                del self._groups[group_name]
    
    def load_from_config(self, groups_config: List[dict]):
        """Load schedules from config."""
        with self._lock:
            self._groups.clear()
            for group in groups_config:
                group_name = group.get("name", "")
                if not group_name:
                    continue
                
                scheduler = GroupScheduler(group_name)
                for s_data in group.get("schedules", []):
                    scheduler.schedules.append(ScheduleEntry.from_dict(s_data))
                
                self._groups[group_name] = scheduler
    
    def save_to_config(self, groups_config: List[dict]) -> List[dict]:
        """Save schedules back to config."""
        with self._lock:
            for group in groups_config:
                group_name = group.get("name", "")
                if group_name in self._groups:
                    group["schedules"] = [
                        s.to_dict() for s in self._groups[group_name].schedules
                    ]
            return groups_config
    
    def check_all(self):
        """Check all groups for scheduled restarts."""
        if not self._restart_callback:
            return
        
        with self._lock:
            for group_scheduler in self._groups.values():
                group_scheduler.check_and_run(self._restart_callback)
    
    def start(self):
        """Start scheduler thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log("SCHEDULER", "Scheduler started")
    
    def stop(self):
        """Stop scheduler thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        log("SCHEDULER", "Scheduler stopped")
    
    def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                self.check_all()
            except Exception as e:
                log("ERROR", f"Scheduler error: {e}")
            
            # Check every 30 seconds
            time.sleep(30)
    
    def get_all_schedules(self) -> List[dict]:
        """Get all schedules across all groups."""
        result = []
        with self._lock:
            for group_name, scheduler in self._groups.items():
                for i, schedule in enumerate(scheduler.schedules):
                    result.append({
                        "group": group_name,
                        "index": i,
                        **schedule.to_dict(),
                        "next_run": schedule.get_next_run().isoformat() if schedule.enabled else None
                    })
        return result


# Global scheduler instance
scheduler = Scheduler()

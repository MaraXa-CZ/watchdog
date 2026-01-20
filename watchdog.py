#!/usr/bin/env python3
"""
Watchdog v3.0 - Network Monitoring Daemon
=========================================
Multi-group server monitoring with automatic power cycling.

© 2026 MaraXa
"""

import subprocess
import time
import signal
import sys

from constants import (
    CONFIG_FILE, PING_TIMEOUT, PING_COUNT, POST_RESET_WAIT,
    VERSION, DEFAULT_CHECK_INTERVAL
)
from config_validator import load_config, ConfigError
from gpio_manager import gpio_manager, GPIOCommand
from logger import log, add_notification_hook
from notifier import configure_notifier, get_notifier, notification_hook
from stats import ping_stats


class WatchdogDaemon:
    """Main watchdog monitoring daemon."""
    
    def __init__(self):
        self.running = True
        self.config = None
        self.initialized_pins = set()
    
    def load_config(self) -> bool:
        """Load and validate configuration."""
        try:
            self.config = load_config()  # Validation and repair is automatic
            return True
        except ConfigError as e:
            log("ERROR", f"Config error: {e.message}")
            return False
        except Exception as e:
            log("ERROR", f"Failed to load config: {e}")
            return False
    
    def init_gpio(self) -> bool:
        """Initialize GPIO pins for all enabled groups."""
        if not self.config:
            return False
        
        outlets = self.config.get("outlets", {})
        groups = self.config.get("groups", [])
        
        initialized = 0
        for group in groups:
            if not group.get("enabled", False):
                continue
            
            outlet_key = group.get("outlet")
            
            # Skip groups with no outlet (stats only)
            if not outlet_key or outlet_key == "none":
                continue
            
            outlet = outlets.get(outlet_key)
            
            if not outlet:
                log("ERROR", f"[{group.get('name', 'Unknown')}] Invalid outlet: {outlet_key}")
                continue
            
            pin = outlet["gpio_pin"]
            if pin not in self.initialized_pins:
                if gpio_manager.init_pin(pin, outlet.get("name", f"GPIO {pin}")):
                    self.initialized_pins.add(pin)
                    initialized += 1
        
        return initialized > 0 or any(g.get("enabled") and g.get("outlet") == "none" for g in groups)
    
    def ping(self, host: str, group_name: str = "Unknown") -> tuple:
        """
        Ping a host.
        Returns (reachable: bool, response_time_ms: float).
        """
        try:
            import time
            start = time.time()
            
            # Run ping and capture output for response time
            proc = subprocess.run(
                ["ping", "-c", str(PING_COUNT), "-W", str(PING_TIMEOUT), host],
                capture_output=True,
                text=True
            )
            
            elapsed = (time.time() - start) * 1000  # Convert to ms
            reachable = proc.returncode == 0
            
            # Try to parse actual response time from ping output
            response_time = 0.0
            if reachable and proc.stdout:
                # Parse "time=X.XX ms" from ping output
                import re
                times = re.findall(r'time[=<](\d+\.?\d*)', proc.stdout)
                if times:
                    response_time = sum(float(t) for t in times) / len(times)
                else:
                    response_time = elapsed / PING_COUNT
            
            # Debug logging
            if self.config.get("system", {}).get("debug", False):
                log("PING", f"[{group_name}] {host}: {'OK' if reachable else 'FAIL'} ({response_time:.1f}ms)")
            elif not reachable:
                log("PING_FAIL", f"[{group_name}] {host} unreachable")
            
            return reachable, response_time
        except Exception as e:
            log("ERROR", f"[{group_name}] Ping exception for {host}: {e}")
            return False, 0.0
    
    def monitor_group(self, group: dict) -> bool:
        """
        Monitor a single server group.
        Returns True if reset was triggered.
        """
        if not group.get("enabled", False) or not group.get("servers"):
            return False
        
        group_name = group.get("name", "Unknown")
        fail_count = group.get("fail_count", self.config.get("fail_count", 3))
        off_time = group.get("off_time", self.config.get("off_time", 10))
        
        # Check if stats are enabled
        stats_enabled = self.config.get("features", {}).get("ping_stats", True)
        
        fails = 0
        
        for i in range(fail_count):
            # Ping all servers in group
            results = {}
            all_failed = True
            
            for server in group["servers"]:
                reachable, response_time = self.ping(server, group_name)
                results[server] = {"reachable": reachable, "response_time": response_time}
                if reachable:
                    all_failed = False
            
            # Record stats (after first ping attempt)
            if i == 0 and stats_enabled:
                ping_stats.record(group_name, results)
            
            # If any server responds, group is OK
            if not all_failed:
                return False
            
            fails += 1
            log("FAIL", f"[{group_name}] All servers unreachable ({fails}/{fail_count})")
            
            if fails < fail_count:
                time.sleep(2)  # Brief wait between attempts
        
        # All attempts failed - trigger reset
        if fails >= fail_count:
            return self.trigger_reset(group, off_time)
        
        return False
    
    def trigger_reset(self, group: dict, off_time: int) -> bool:
        """Trigger power reset for a group."""
        group_name = group.get("name", "Unknown")
        outlet_key = group.get("outlet")
        
        # Stats-only group (no outlet)
        if not outlet_key or outlet_key == "none":
            log("FAIL", f"[{group_name}] Servers unreachable (stats-only mode, no reset)")
            # Notify via email
            notifier = get_notifier()
            notifier.notify_reset(
                group_name=group_name,
                servers=group.get("servers", []),
                gpio_pin=None,
                off_time=0
            )
            return False
        
        outlets = self.config.get("outlets", {})
        outlet = outlets.get(outlet_key)
        
        if not outlet:
            log("ERROR", f"[{group_name}] Cannot reset - invalid outlet")
            return False
        
        pin = outlet["gpio_pin"]
        
        log("RESET", f"[{group_name}] Triggering power cut for {off_time}s on GPIO {pin}")
        
        # Notify via email
        notifier = get_notifier()
        notifier.notify_reset(
            group_name=group_name,
            servers=group.get("servers", []),
            gpio_pin=pin,
            off_time=off_time
        )
        
        # Execute reset
        if gpio_manager.restart_pin(pin, off_time):
            log("RESET", f"[{group_name}] Power restored, waiting {POST_RESET_WAIT}s")
            time.sleep(POST_RESET_WAIT)
            return True
        else:
            log("ERROR", f"[{group_name}] Reset failed")
            return False
    
    def process_commands(self):
        """Process any pending commands from web interface."""
        outlets = self.config.get("outlets", {})
        processed = gpio_manager.process_commands(outlets)
        if processed > 0:
            log("INFO", f"Processed {processed} command(s)")
    
    def cleanup(self):
        """Clean shutdown."""
        self.running = False
        log("SHUTDOWN", "Stopping watchdog daemon")
        gpio_manager.cleanup()
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.cleanup()
        sys.exit(0)
    
    def run(self):
        """Main daemon loop."""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Initial config load
        if not self.load_config():
            log("ERROR", "Cannot start - config load failed")
            sys.exit(1)
        
        # Configure email notifications
        smtp_config = self.config.get("smtp", {})
        configure_notifier(smtp_config)
        add_notification_hook(notification_hook)
        
        # Initialize GPIO
        if not self.init_gpio():
            log("ERROR", "No enabled groups with valid GPIO. Exiting.")
            sys.exit(1)
        
        # Count enabled groups
        enabled_groups = [g for g in self.config.get("groups", []) if g.get("enabled", False)]
        log("INIT", f"Watchdog v{VERSION} started - monitoring {len(enabled_groups)} group(s)")
        
        # Notify startup
        hostname = self.config.get("system", {}).get("hostname", "watchdog")
        get_notifier().notify_startup(len(enabled_groups), hostname)
        
        # Main monitoring loop
        while self.running:
            try:
                # Reload config each cycle (allows live changes)
                self.load_config()
                
                # Process any pending web commands
                self.process_commands()
                
                # Clear old stale commands
                gpio_manager.clear_old_commands(max_age_seconds=300)
                
                # Monitor each enabled group
                for group in self.config.get("groups", []):
                    if not self.running:
                        break
                    
                    if group.get("enabled", False) and group.get("servers"):
                        self.monitor_group(group)
                
                # Wait for next cycle
                interval = self.config.get("check_interval", DEFAULT_CHECK_INTERVAL)
                time.sleep(interval)
                
            except Exception as e:
                log("ERROR", f"Main loop error: {e}")
                time.sleep(10)


def main():
    """Entry point."""
    daemon = WatchdogDaemon()
    daemon.run()


if __name__ == "__main__":
    main()

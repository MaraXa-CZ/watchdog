"""
Watchdog v3.0 - GPIO Manager
============================
Singleton pattern for GPIO control with command queue.
Prevents race conditions between web interface and watchdog daemon.

Supports: Raspberry Pi 1-5
- Pi 1-4: Uses RPi.GPIO backend (default)
- Pi 5: Uses lgpio backend (auto-detected)
"""

import os
import json
import time
import threading
import fcntl
from datetime import datetime
from typing import Dict, Optional, Callable
from enum import Enum

# Auto-detect Pi model and select appropriate GPIO backend
PI5_MODE = False
GPIO_AVAILABLE = False

try:
    # Check if running on Pi 5
    if os.path.exists('/proc/device-tree/model'):
        with open('/proc/device-tree/model') as f:
            model = f.read()
            if 'Pi 5' in model:
                PI5_MODE = True
    
    from gpiozero import OutputDevice
    
    # For Pi 5, try to use lgpio backend
    if PI5_MODE:
        try:
            from gpiozero.pins.lgpio import LGPIOFactory
            from gpiozero import Device
            Device.pin_factory = LGPIOFactory()
            print("GPIO: Using lgpio backend (Pi 5)")
        except ImportError:
            print("WARNING: lgpio not available, GPIO may not work on Pi 5")
            print("Install with: sudo apt install python3-lgpio")
    
    GPIO_AVAILABLE = True

except ImportError:
    GPIO_AVAILABLE = False
    OutputDevice = None

from constants import COMMAND_DIR, VALID_GPIO_PINS
from logger import log


class GPIOCommand(Enum):
    """Available GPIO commands."""
    ON = "on"
    OFF = "off"
    RESTART = "restart"


class GPIOManager:
    """
    Singleton GPIO manager with file-based command queue.
    
    Architecture:
    - Only ONE process (watchdog daemon) directly controls GPIO
    - Web interface writes commands to /opt/watchdog/commands/
    - Daemon reads and executes commands
    - Prevents race conditions and GPIO conflicts
    """
    
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
        self._relays: Dict[int, OutputDevice] = {}
        self._gpio_lock = threading.Lock()
        self._command_callbacks: Dict[str, Callable] = {}
        
        # Ensure command directory exists
        os.makedirs(COMMAND_DIR, exist_ok=True)
    
    def init_pin(self, pin: int, name: str = "") -> bool:
        """
        Initialize GPIO pin for output.
        Returns True if successful.
        """
        if not GPIO_AVAILABLE:
            log("GPIO", f"GPIO not available (simulation mode)")
            return True
        
        if pin not in VALID_GPIO_PINS:
            log("ERROR", f"Invalid GPIO pin: {pin}")
            return False
        
        with self._gpio_lock:
            if pin in self._relays:
                return True  # Already initialized
            
            try:
                self._relays[pin] = OutputDevice(pin)
                log("INIT", f"GPIO {pin} initialized ({name})")
                return True
            except Exception as e:
                log("ERROR", f"GPIO {pin} init failed: {e}")
                return False
    
    def set_pin(self, pin: int, state: bool) -> bool:
        """
        Set GPIO pin state directly.
        Only use from daemon process!
        """
        if not GPIO_AVAILABLE:
            log("GPIO", f"Pin {pin} -> {'ON' if state else 'OFF'} (simulated)")
            return True
        
        with self._gpio_lock:
            if pin not in self._relays:
                log("ERROR", f"GPIO {pin} not initialized")
                return False
            
            try:
                if state:
                    self._relays[pin].on()
                else:
                    self._relays[pin].off()
                return True
            except Exception as e:
                log("ERROR", f"GPIO {pin} set failed: {e}")
                return False
    
    def restart_pin(self, pin: int, off_time: int = 10) -> bool:
        """
        Power cycle: ON (relay activated = power cut) -> wait -> OFF (power restored)
        Only use from daemon process!
        """
        if not GPIO_AVAILABLE:
            log("GPIO", f"Pin {pin} restart for {off_time}s (simulated)")
            return True
        
        with self._gpio_lock:
            if pin not in self._relays:
                log("ERROR", f"GPIO {pin} not initialized")
                return False
            
            try:
                relay = self._relays[pin]
                relay.on()  # Cut power
                time.sleep(off_time)
                relay.off()  # Restore power
                return True
            except Exception as e:
                log("ERROR", f"GPIO {pin} restart failed: {e}")
                return False
    
    def cleanup(self):
        """Release all GPIO resources."""
        with self._gpio_lock:
            for pin, relay in self._relays.items():
                try:
                    relay.off()
                    relay.close()
                except:
                    pass
            self._relays.clear()
            log("SHUTDOWN", "GPIO resources released")
    
    # ==================== COMMAND QUEUE SYSTEM ====================
    
    def queue_command(self, group_name: str, outlet_key: str, command: GPIOCommand, 
                      off_time: int = 10, source: str = "web") -> str:
        """
        Queue a command for the daemon to execute.
        Used by web interface to avoid direct GPIO access.
        Returns command ID.
        """
        command_id = f"{int(time.time() * 1000)}"
        command_file = os.path.join(COMMAND_DIR, f"{command_id}.cmd")
        
        cmd_data = {
            "id": command_id,
            "timestamp": datetime.now().isoformat(),
            "group_name": group_name,
            "outlet_key": outlet_key,
            "command": command.value,
            "off_time": off_time,
            "source": source,
            "status": "pending"
        }
        
        try:
            with open(command_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(cmd_data, f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            log("COMMAND", f"Queued {command.value} for [{group_name}] from {source}")
            return command_id
        except Exception as e:
            log("ERROR", f"Failed to queue command: {e}")
            return ""
    
    def process_commands(self, outlets_config: dict) -> int:
        """
        Process pending commands from queue.
        Called by daemon in main loop.
        Returns number of commands processed.
        """
        if not os.path.exists(COMMAND_DIR):
            return 0
        
        processed = 0
        
        for filename in sorted(os.listdir(COMMAND_DIR)):
            if not filename.endswith('.cmd'):
                continue
            
            cmd_path = os.path.join(COMMAND_DIR, filename)
            
            try:
                with open(cmd_path, 'r') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    cmd_data = json.load(f)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                
                if cmd_data.get("status") != "pending":
                    os.remove(cmd_path)
                    continue
                
                # Execute command
                outlet_key = cmd_data.get("outlet_key")
                outlet = outlets_config.get(outlet_key)
                
                if not outlet:
                    log("ERROR", f"Unknown outlet: {outlet_key}")
                    os.remove(cmd_path)
                    continue
                
                pin = outlet["gpio_pin"]
                command = cmd_data.get("command")
                group_name = cmd_data.get("group_name", "Unknown")
                
                if command == "on":
                    self.set_pin(pin, True)
                    log("MANUAL", f"[{group_name}] Power ON via {cmd_data.get('source', 'unknown')}")
                elif command == "off":
                    self.set_pin(pin, False)
                    log("MANUAL", f"[{group_name}] Power OFF via {cmd_data.get('source', 'unknown')}")
                elif command == "restart":
                    off_time = cmd_data.get("off_time", 10)
                    log("MANUAL", f"[{group_name}] Manual restart for {off_time}s")
                    self.restart_pin(pin, off_time)
                    log("MANUAL", f"[{group_name}] Power restored")
                
                # Remove processed command
                os.remove(cmd_path)
                processed += 1
                
            except json.JSONDecodeError:
                log("ERROR", f"Invalid command file: {filename}")
                os.remove(cmd_path)
            except Exception as e:
                log("ERROR", f"Command processing error: {e}")
        
        return processed
    
    def get_pending_commands(self) -> list:
        """Get list of pending commands."""
        if not os.path.exists(COMMAND_DIR):
            return []
        
        commands = []
        for filename in os.listdir(COMMAND_DIR):
            if filename.endswith('.cmd'):
                try:
                    with open(os.path.join(COMMAND_DIR, filename)) as f:
                        commands.append(json.load(f))
                except:
                    pass
        
        return sorted(commands, key=lambda x: x.get("timestamp", ""))
    
    def clear_old_commands(self, max_age_seconds: int = 300):
        """Remove commands older than max_age_seconds."""
        if not os.path.exists(COMMAND_DIR):
            return
        
        now = time.time()
        for filename in os.listdir(COMMAND_DIR):
            if filename.endswith('.cmd'):
                filepath = os.path.join(COMMAND_DIR, filename)
                try:
                    if now - os.path.getmtime(filepath) > max_age_seconds:
                        os.remove(filepath)
                except:
                    pass


# Global instance
gpio_manager = GPIOManager()

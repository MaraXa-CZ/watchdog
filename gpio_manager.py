"""
Watchdog v5.0 - Universal GPIO Manager
======================================
Supports multiple GPIO backends for maximum compatibility:
- gpiod (libgpiod) - Debian 13+ (Trixie), future standard
- lgpio - Raspberry Pi 5, Bookworm+
- gpiozero/RPi.GPIO - Legacy Pi 1-4

Auto-detects the best available backend based on OS and hardware.
"""

import os
import json
import time
import threading
import fcntl
from datetime import datetime
from typing import Dict, Optional, Callable
from enum import Enum

from constants import COMMAND_DIR, VALID_GPIO_PINS
from logger import log


# ============================================================================
# Helper Functions
# ============================================================================

def _is_pi5() -> bool:
    """Detect Raspberry Pi 5."""
    try:
        with open('/proc/device-tree/model') as f:
            return 'Pi 5' in f.read()
    except:
        return False


def _get_os_version() -> int:
    """Get Debian/Raspbian major version number."""
    try:
        with open('/etc/debian_version') as f:
            version = f.read().strip()
            if '/' in version:
                codenames = {'bullseye': 11, 'bookworm': 12, 'trixie': 13, 'forky': 14}
                name = version.split('/')[0].lower()
                return codenames.get(name, 12)
            else:
                return int(float(version))
    except:
        return 12


# ============================================================================
# GPIO Backend Classes
# ============================================================================

class GPIOBackend:
    """Abstract GPIO backend interface."""
    
    name = "base"
    
    def __init__(self):
        self.initialized_pins = {}
    
    def setup_output(self, pin: int, name: str = "") -> bool:
        raise NotImplementedError
    
    def write(self, pin: int, value: bool) -> bool:
        raise NotImplementedError
    
    def read(self, pin: int) -> Optional[bool]:
        raise NotImplementedError
    
    def cleanup(self, pin: int = None):
        raise NotImplementedError


class GPIOdBackend(GPIOBackend):
    """libgpiod backend for Debian 13+ (Trixie)."""
    
    name = "gpiod"
    
    def __init__(self):
        super().__init__()
        import gpiod
        self.gpiod = gpiod
        
        # Pi 5: gpiochip4, Pi 4 and older: gpiochip0
        chip_name = "gpiochip4" if _is_pi5() else "gpiochip0"
        
        try:
            self.chip = gpiod.Chip(chip_name)
        except:
            self.chip = gpiod.Chip("gpiochip0")
            chip_name = "gpiochip0"
        
        self.lines = {}
        log("GPIO", f"Using gpiod backend with {chip_name}")
    
    def setup_output(self, pin: int, name: str = "") -> bool:
        try:
            # gpiod v2.x API
            if hasattr(self.gpiod, 'LineSettings'):
                config = self.gpiod.LineSettings(
                    direction=self.gpiod.line.Direction.OUTPUT,
                    output_value=self.gpiod.line.Value.INACTIVE
                )
                line = self.chip.request_lines(
                    consumer=f"watchdog-{name or pin}",
                    config={pin: config}
                )
            else:
                # gpiod v1.x API fallback
                line = self.chip.get_line(pin)
                line.request(consumer=f"watchdog-{name or pin}", 
                           type=self.gpiod.LINE_REQ_DIR_OUT)
            
            self.lines[pin] = line
            self.initialized_pins[pin] = name
            return True
        except Exception as e:
            log("ERROR", f"gpiod setup failed for pin {pin}: {e}")
            return False
    
    def write(self, pin: int, value: bool) -> bool:
        try:
            if pin not in self.lines:
                return False
            
            line = self.lines[pin]
            
            # gpiod v2.x
            if hasattr(self.gpiod, 'line') and hasattr(self.gpiod.line, 'Value'):
                val = self.gpiod.line.Value.ACTIVE if value else self.gpiod.line.Value.INACTIVE
                line.set_value(pin, val)
            else:
                # gpiod v1.x
                line.set_value(1 if value else 0)
            
            return True
        except Exception as e:
            log("ERROR", f"gpiod write failed for pin {pin}: {e}")
            return False
    
    def read(self, pin: int) -> Optional[bool]:
        try:
            if pin not in self.lines:
                return None
            
            line = self.lines[pin]
            
            if hasattr(self.gpiod, 'line') and hasattr(self.gpiod.line, 'Value'):
                val = line.get_value(pin)
                return val == self.gpiod.line.Value.ACTIVE
            else:
                return line.get_value() == 1
        except:
            return None
    
    def cleanup(self, pin: int = None):
        try:
            if pin and pin in self.lines:
                self.lines[pin].release()
                del self.lines[pin]
                self.initialized_pins.pop(pin, None)
            elif pin is None:
                for line in self.lines.values():
                    try:
                        line.release()
                    except:
                        pass
                self.lines.clear()
                self.initialized_pins.clear()
        except Exception as e:
            log("ERROR", f"gpiod cleanup failed: {e}")


class LGPIOBackend(GPIOBackend):
    """lgpio backend for Raspberry Pi 5."""
    
    name = "lgpio"
    
    def __init__(self):
        super().__init__()
        import lgpio
        self.lgpio = lgpio
        self.chip = lgpio.gpiochip_open(0)
        log("GPIO", "Using lgpio backend")
    
    def setup_output(self, pin: int, name: str = "") -> bool:
        try:
            self.lgpio.gpio_claim_output(self.chip, pin, 0)
            self.initialized_pins[pin] = name
            return True
        except Exception as e:
            log("ERROR", f"lgpio setup failed for pin {pin}: {e}")
            return False
    
    def write(self, pin: int, value: bool) -> bool:
        try:
            self.lgpio.gpio_write(self.chip, pin, 1 if value else 0)
            return True
        except Exception as e:
            log("ERROR", f"lgpio write failed for pin {pin}: {e}")
            return False
    
    def read(self, pin: int) -> Optional[bool]:
        try:
            return self.lgpio.gpio_read(self.chip, pin) == 1
        except:
            return None
    
    def cleanup(self, pin: int = None):
        try:
            if pin is None:
                self.lgpio.gpiochip_close(self.chip)
                self.initialized_pins.clear()
        except Exception as e:
            log("ERROR", f"lgpio cleanup failed: {e}")


class GPIOZeroBackend(GPIOBackend):
    """gpiozero backend for Pi 1-4 (uses RPi.GPIO internally)."""
    
    name = "gpiozero"
    
    def __init__(self):
        super().__init__()
        from gpiozero import OutputDevice
        self.OutputDevice = OutputDevice
        self.devices = {}
        log("GPIO", "Using gpiozero backend")
    
    def setup_output(self, pin: int, name: str = "") -> bool:
        try:
            device = self.OutputDevice(pin, initial_value=False)
            self.devices[pin] = device
            self.initialized_pins[pin] = name
            return True
        except Exception as e:
            log("ERROR", f"gpiozero setup failed for pin {pin}: {e}")
            return False
    
    def write(self, pin: int, value: bool) -> bool:
        try:
            if pin not in self.devices:
                return False
            if value:
                self.devices[pin].on()
            else:
                self.devices[pin].off()
            return True
        except Exception as e:
            log("ERROR", f"gpiozero write failed for pin {pin}: {e}")
            return False
    
    def read(self, pin: int) -> Optional[bool]:
        try:
            if pin in self.devices:
                return self.devices[pin].value == 1
            return None
        except:
            return None
    
    def cleanup(self, pin: int = None):
        try:
            if pin and pin in self.devices:
                self.devices[pin].close()
                del self.devices[pin]
                self.initialized_pins.pop(pin, None)
            elif pin is None:
                for device in self.devices.values():
                    device.close()
                self.devices.clear()
                self.initialized_pins.clear()
        except Exception as e:
            log("ERROR", f"gpiozero cleanup failed: {e}")


class DummyBackend(GPIOBackend):
    """Dummy backend when no GPIO is available."""
    
    name = "dummy"
    
    def __init__(self):
        super().__init__()
        self.pin_states = {}
        log("GPIO", "Using dummy backend (no real GPIO)")
    
    def setup_output(self, pin: int, name: str = "") -> bool:
        self.pin_states[pin] = False
        self.initialized_pins[pin] = name
        return True
    
    def write(self, pin: int, value: bool) -> bool:
        self.pin_states[pin] = value
        return True
    
    def read(self, pin: int) -> Optional[bool]:
        return self.pin_states.get(pin)
    
    def cleanup(self, pin: int = None):
        if pin:
            self.pin_states.pop(pin, None)
            self.initialized_pins.pop(pin, None)
        else:
            self.pin_states.clear()
            self.initialized_pins.clear()


# ============================================================================
# Backend Detection
# ============================================================================

def _detect_best_backend() -> GPIOBackend:
    """Auto-detect and return the best available GPIO backend."""
    
    os_version = _get_os_version()
    is_pi5 = _is_pi5()
    
    log("GPIO", f"Detecting backend: OS version={os_version}, Pi5={is_pi5}")
    
    # Priority based on OS and hardware
    if os_version >= 13:
        backends_to_try = ['gpiod', 'lgpio', 'gpiozero']
    elif is_pi5:
        backends_to_try = ['lgpio', 'gpiod', 'gpiozero']
    else:
        backends_to_try = ['gpiozero', 'lgpio', 'gpiod']
    
    for backend_name in backends_to_try:
        try:
            if backend_name == 'gpiod':
                import gpiod
                return GPIOdBackend()
            elif backend_name == 'lgpio':
                import lgpio
                return LGPIOBackend()
            elif backend_name == 'gpiozero':
                from gpiozero import OutputDevice
                return GPIOZeroBackend()
        except ImportError:
            log("GPIO", f"Backend {backend_name} not available")
        except Exception as e:
            log("GPIO", f"Backend {backend_name} init failed: {e}")
    
    return DummyBackend()


# ============================================================================
# GPIO Command Enum
# ============================================================================

class GPIOCommand(Enum):
    """Available GPIO commands."""
    ON = "on"
    OFF = "off"
    RESTART = "restart"


# ============================================================================
# GPIO Manager (Singleton)
# ============================================================================

class GPIOManager:
    """Thread-safe GPIO manager with command queue."""
    
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
        self._gpio_lock = threading.Lock()
        
        # Initialize GPIO backend
        self._backend = _detect_best_backend()
        self._gpio_available = not isinstance(self._backend, DummyBackend)
        
        # Ensure command directory exists
        os.makedirs(COMMAND_DIR, exist_ok=True)
        
        log("GPIO", f"Manager initialized, backend={self._backend.name}, available={self._gpio_available}")
    
    @property
    def gpio_available(self) -> bool:
        return self._gpio_available
    
    @property
    def backend_name(self) -> str:
        return self._backend.name
    
    def init_pin(self, pin: int, name: str = "") -> bool:
        """Initialize a GPIO pin as output."""
        if pin not in VALID_GPIO_PINS:
            log("ERROR", f"Invalid GPIO pin: {pin}")
            return False
        
        with self._gpio_lock:
            return self._backend.setup_output(pin, name)
    
    def set_pin(self, pin: int, state: bool) -> bool:
        """Set GPIO pin state."""
        with self._gpio_lock:
            success = self._backend.write(pin, state)
            if success:
                log("GPIO", f"Pin {pin} -> {'ON' if state else 'OFF'}")
            return success
    
    def get_pin_state(self, pin: int) -> Optional[bool]:
        """Get current pin state."""
        with self._gpio_lock:
            return self._backend.read(pin)
    
    def queue_command(self, pin: int, command: GPIOCommand, 
                      source: str = "unknown", off_time: int = 10) -> bool:
        """Queue a command for watchdog daemon to execute."""
        if pin not in VALID_GPIO_PINS:
            log("ERROR", f"Invalid GPIO pin for command: {pin}")
            return False
        
        cmd_data = {
            "pin": pin,
            "command": command.value,
            "source": source,
            "off_time": off_time,
            "timestamp": datetime.now().isoformat(),
            "processed": False
        }
        
        cmd_file = os.path.join(COMMAND_DIR, f"cmd_{pin}_{int(time.time()*1000)}.json")
        
        try:
            fd = os.open(cmd_file, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o644)
            with os.fdopen(fd, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(cmd_data, f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            log("GPIO", f"Command queued: pin={pin}, cmd={command.value}")
            return True
            
        except Exception as e:
            log("ERROR", f"Failed to queue command: {e}")
            return False
    
    def process_commands(self, callback: Callable[[int, GPIOCommand, int], bool] = None) -> int:
        """Process pending commands. Called by watchdog daemon."""
        processed = 0
        
        try:
            cmd_files = sorted([
                f for f in os.listdir(COMMAND_DIR) 
                if f.startswith('cmd_') and f.endswith('.json')
            ])
        except FileNotFoundError:
            return 0
        
        for cmd_file in cmd_files:
            cmd_path = os.path.join(COMMAND_DIR, cmd_file)
            
            try:
                with open(cmd_path, 'r') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    cmd_data = json.load(f)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                
                if cmd_data.get("processed"):
                    os.remove(cmd_path)
                    continue
                
                pin = cmd_data["pin"]
                command = GPIOCommand(cmd_data["command"])
                off_time = cmd_data.get("off_time", 10)
                
                if callback:
                    success = callback(pin, command, off_time)
                else:
                    success = self._execute_command(pin, command, off_time)
                
                if success:
                    processed += 1
                
                os.remove(cmd_path)
                
            except Exception as e:
                log("ERROR", f"Failed to process command {cmd_file}: {e}")
                try:
                    os.remove(cmd_path)
                except:
                    pass
        
        return processed
    
    def _execute_command(self, pin: int, command: GPIOCommand, off_time: int = 10) -> bool:
        """Execute a GPIO command directly."""
        try:
            if command == GPIOCommand.ON:
                return self.set_pin(pin, True)
            
            elif command == GPIOCommand.OFF:
                return self.set_pin(pin, False)
            
            elif command == GPIOCommand.RESTART:
                self.set_pin(pin, False)
                log("GPIO", f"Pin {pin} OFF for {off_time}s")
                time.sleep(off_time)
                self.set_pin(pin, True)
                log("GPIO", f"Pin {pin} ON")
                return True
            
            return False
            
        except Exception as e:
            log("ERROR", f"Command execution failed: {e}")
            return False
    
    def cleanup(self):
        """Cleanup GPIO resources."""
        with self._gpio_lock:
            self._backend.cleanup()
        log("GPIO", "Cleanup complete")
    
    def get_initialized_pins(self) -> Dict[int, str]:
        """Get dict of initialized pins."""
        return dict(self._backend.initialized_pins)


# Global singleton instance
gpio_manager = GPIOManager()

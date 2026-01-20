"""
Watchdog v5.0 - Network Manager
===============================
Real network configuration for Raspberry Pi.
Supports:
- dhcpcd (Raspberry Pi OS Bullseye/Bookworm)
- netplan (Ubuntu)
- NetworkManager (Raspberry Pi OS Trixie+, modern distros)

WARNING: Incorrect configuration can make the device unreachable!
"""

import os
import subprocess
import re
import shutil
import time
import threading
from datetime import datetime
from typing import Dict, Optional, Tuple, List

from logger import log


class NetworkManager:
    """Manages real system network configuration."""
    
    # Configuration file paths
    DHCPCD_CONF = "/etc/dhcpcd.conf"
    NETPLAN_DIR = "/etc/netplan"
    RESOLV_CONF = "/etc/resolv.conf"
    NM_CONN_DIR = "/etc/NetworkManager/system-connections"
    
    # Backup directory
    BACKUP_DIR = "/opt/watchdog/backups/network"
    
    # Rollback timeout (seconds) - if user doesn't confirm, revert changes
    ROLLBACK_TIMEOUT = 120
    
    def __init__(self):
        self._rollback_timer = None
        self._pending_backup = None
        os.makedirs(self.BACKUP_DIR, exist_ok=True)
    
    def get_network_type(self) -> str:
        """Detect which network configuration system is in use."""
        # 1. Check if NetworkManager is active (Trixie+, modern distros)
        if self._is_networkmanager_active():
            return "networkmanager"
        
        # 2. dhcpcd (Raspberry Pi OS Bullseye/Bookworm)
        if os.path.exists(self.DHCPCD_CONF):
            # Make sure dhcpcd service exists
            try:
                result = subprocess.run(["systemctl", "is-enabled", "dhcpcd"], 
                                       capture_output=True, text=True)
                if result.returncode == 0:
                    return "dhcpcd"
            except:
                pass
        
        # 3. netplan (Ubuntu)
        if os.path.isdir(self.NETPLAN_DIR) and os.listdir(self.NETPLAN_DIR):
            return "netplan"
        
        # 4. Fallback to dhcpcd if config exists
        if os.path.exists(self.DHCPCD_CONF):
            return "dhcpcd"
        
        return "unknown"
    
    def _is_networkmanager_active(self) -> bool:
        """Check if NetworkManager is the active network service."""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "NetworkManager"],
                capture_output=True, text=True
            )
            return result.stdout.strip() == "active"
        except:
            return False
    
    def get_interfaces(self) -> List[str]:
        """Get list of network interfaces."""
        interfaces = []
        try:
            output = subprocess.check_output(["ip", "link", "show"], text=True)
            for line in output.split('\n'):
                match = re.match(r'^\d+:\s+(\w+):', line)
                if match:
                    iface = match.group(1)
                    if iface not in ['lo']:  # Exclude loopback
                        interfaces.append(iface)
        except Exception as e:
            log("ERROR", f"Failed to get interfaces: {e}")
        return interfaces
    
    def get_primary_interface(self) -> str:
        """Get primary network interface (eth0 or wlan0)."""
        interfaces = self.get_interfaces()
        # Prefer eth0, then wlan0, then first available
        for preferred in ['eth0', 'wlan0', 'enp0s3', 'ens33']:
            if preferred in interfaces:
                return preferred
        return interfaces[0] if interfaces else 'eth0'
    
    def get_current_config(self) -> Dict:
        """Get current network configuration from system."""
        config = {
            "interface": self.get_primary_interface(),
            "mode": "dhcp",
            "ip_address": "",
            "netmask": "255.255.255.0",
            "gateway": "",
            "dns_servers": [],
            "network_type": self.get_network_type()
        }
        
        try:
            # Get current IP from ip command
            iface = config["interface"]
            output = subprocess.check_output(["ip", "addr", "show", iface], text=True)
            
            # Parse IP address
            ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)', output)
            if ip_match:
                config["ip_address"] = ip_match.group(1)
                # Convert CIDR to netmask
                cidr = int(ip_match.group(2))
                config["netmask"] = self._cidr_to_netmask(cidr)
            
            # Get gateway
            route_output = subprocess.check_output(["ip", "route", "show", "default"], text=True)
            gw_match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', route_output)
            if gw_match:
                config["gateway"] = gw_match.group(1)
            
            # Get DNS servers
            if os.path.exists(self.RESOLV_CONF):
                with open(self.RESOLV_CONF) as f:
                    for line in f:
                        if line.startswith('nameserver'):
                            dns = line.split()[1]
                            if dns not in config["dns_servers"]:
                                config["dns_servers"].append(dns)
            
            # Check if static IP is configured
            if config["network_type"] == "dhcpcd":
                config["mode"] = self._get_dhcpcd_mode(iface)
            elif config["network_type"] == "netplan":
                config["mode"] = self._get_netplan_mode(iface)
                
        except Exception as e:
            log("ERROR", f"Failed to get current network config: {e}")
        
        return config
    
    def _cidr_to_netmask(self, cidr: int) -> str:
        """Convert CIDR notation to dotted netmask."""
        mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
        return f"{(mask >> 24) & 0xff}.{(mask >> 16) & 0xff}.{(mask >> 8) & 0xff}.{mask & 0xff}"
    
    def _netmask_to_cidr(self, netmask: str) -> int:
        """Convert dotted netmask to CIDR notation."""
        try:
            parts = [int(x) for x in netmask.split('.')]
            binary = ''.join(format(x, '08b') for x in parts)
            return binary.count('1')
        except:
            return 24
    
    def _get_dhcpcd_mode(self, interface: str) -> str:
        """Check if static IP is configured in dhcpcd.conf."""
        try:
            if os.path.exists(self.DHCPCD_CONF):
                with open(self.DHCPCD_CONF) as f:
                    lines = f.readlines()
                
                in_interface_block = False
                for line in lines:
                    # Skip comments
                    stripped = line.strip()
                    if stripped.startswith('#') or not stripped:
                        continue
                    
                    # Check for interface block start
                    if stripped.startswith('interface '):
                        in_interface_block = (interface in stripped)
                        continue
                    
                    # If in our interface block, look for static ip_address
                    if in_interface_block and stripped.startswith('static ip_address'):
                        return "static"
                    
                    # New interface block means we left our block
                    if stripped.startswith('interface '):
                        in_interface_block = False
                        
        except Exception as e:
            log("ERROR", f"Failed to read dhcpcd.conf: {e}")
        return "dhcp"
    
    def _get_netplan_mode(self, interface: str) -> str:
        """Check if static IP is configured in netplan."""
        try:
            for filename in os.listdir(self.NETPLAN_DIR):
                if filename.endswith('.yaml') or filename.endswith('.yml'):
                    filepath = os.path.join(self.NETPLAN_DIR, filename)
                    with open(filepath) as f:
                        content = f.read()
                        if interface in content and 'dhcp4: false' in content:
                            return "static"
        except Exception as e:
            log("ERROR", f"Failed to read netplan: {e}")
        return "dhcp"
    
    def validate_config(self, config: Dict) -> Tuple[bool, str]:
        """Validate network configuration."""
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        
        if config.get("mode") == "static":
            # Validate IP address
            ip = config.get("static_ip", "")
            if not ip or not re.match(ip_pattern, ip):
                return False, "Neplatná IP adresa"
            
            # Validate netmask
            netmask = config.get("netmask", "")
            if not netmask or not re.match(ip_pattern, netmask):
                return False, "Neplatná maska sítě"
            
            # Validate gateway
            gateway = config.get("gateway", "")
            if not gateway or not re.match(ip_pattern, gateway):
                return False, "Neplatná výchozí brána"
            
            # Check if IP parts are valid (0-255)
            for ip_str in [ip, netmask, gateway]:
                parts = [int(x) for x in ip_str.split('.')]
                if any(p < 0 or p > 255 for p in parts):
                    return False, f"Neplatná hodnota v adrese: {ip_str}"
        
        # Validate DNS servers
        for dns in config.get("dns_servers", []):
            if dns and not re.match(ip_pattern, dns):
                return False, f"Neplatná DNS adresa: {dns}"
        
        return True, ""
    
    def backup_config(self) -> str:
        """Create backup of current network configuration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.BACKUP_DIR, timestamp)
        os.makedirs(backup_path, exist_ok=True)
        
        network_type = self.get_network_type()
        
        try:
            # Backup dhcpcd.conf
            if os.path.exists(self.DHCPCD_CONF):
                shutil.copy2(self.DHCPCD_CONF, os.path.join(backup_path, "dhcpcd.conf"))
            
            # Backup netplan files
            if os.path.isdir(self.NETPLAN_DIR):
                netplan_backup = os.path.join(backup_path, "netplan")
                os.makedirs(netplan_backup, exist_ok=True)
                for f in os.listdir(self.NETPLAN_DIR):
                    if f.endswith(('.yaml', '.yml')):
                        shutil.copy2(
                            os.path.join(self.NETPLAN_DIR, f),
                            os.path.join(netplan_backup, f)
                        )
            
            # Backup NetworkManager connections
            if network_type == "networkmanager" and os.path.isdir(self.NM_CONN_DIR):
                nm_backup = os.path.join(backup_path, "NetworkManager")
                os.makedirs(nm_backup, exist_ok=True)
                
                # Save current connection info
                interface = self.get_primary_interface()
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "NAME,UUID,DEVICE", "connection", "show", "--active"],
                    capture_output=True, text=True
                )
                
                with open(os.path.join(nm_backup, "active_connections.txt"), 'w') as f:
                    f.write(result.stdout)
                
                # Backup watchdog connection files
                for f in os.listdir(self.NM_CONN_DIR):
                    if f.startswith("watchdog-"):
                        shutil.copy2(
                            os.path.join(self.NM_CONN_DIR, f),
                            os.path.join(nm_backup, f)
                        )
            
            # Save network type
            with open(os.path.join(backup_path, "network_type.txt"), 'w') as f:
                f.write(network_type)
            
            log("NETWORK", f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            log("ERROR", f"Failed to create backup: {e}")
            return ""
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore network configuration from backup."""
        try:
            # Read network type from backup
            network_type_file = os.path.join(backup_path, "network_type.txt")
            if os.path.exists(network_type_file):
                with open(network_type_file) as f:
                    backup_network_type = f.read().strip()
            else:
                backup_network_type = self.get_network_type()
            
            # Restore dhcpcd.conf
            dhcpcd_backup = os.path.join(backup_path, "dhcpcd.conf")
            if os.path.exists(dhcpcd_backup):
                shutil.copy2(dhcpcd_backup, self.DHCPCD_CONF)
                log("NETWORK", "Restored dhcpcd.conf from backup")
            
            # Restore netplan files
            netplan_backup = os.path.join(backup_path, "netplan")
            if os.path.isdir(netplan_backup):
                for f in os.listdir(netplan_backup):
                    shutil.copy2(
                        os.path.join(netplan_backup, f),
                        os.path.join(self.NETPLAN_DIR, f)
                    )
                log("NETWORK", "Restored netplan from backup")
            
            # Restore NetworkManager
            nm_backup = os.path.join(backup_path, "NetworkManager")
            if os.path.isdir(nm_backup):
                interface = self.get_primary_interface()
                
                # Delete current watchdog connection
                subprocess.run(
                    ["nmcli", "connection", "delete", f"watchdog-{interface}"],
                    capture_output=True
                )
                
                # Restore connection files
                for f in os.listdir(nm_backup):
                    if f.startswith("watchdog-") and f.endswith(".nmconnection"):
                        shutil.copy2(
                            os.path.join(nm_backup, f),
                            os.path.join(self.NM_CONN_DIR, f)
                        )
                
                # Reload connections
                subprocess.run(["nmcli", "connection", "reload"], capture_output=True)
                log("NETWORK", "Restored NetworkManager from backup")
            
            # Apply restored configuration
            self._apply_network_changes()
            return True
            
        except Exception as e:
            log("ERROR", f"Failed to restore backup: {e}")
            return False
            return False
    
    def apply_config(self, config: Dict, with_rollback: bool = True) -> Tuple[bool, str]:
        """
        Apply network configuration to system.
        
        Args:
            config: Network configuration dict
            with_rollback: If True, schedule automatic rollback if not confirmed
            
        Returns:
            (success, message)
        """
        # Validate first
        valid, error = self.validate_config(config)
        if not valid:
            return False, error
        
        # Create backup
        backup_path = self.backup_config()
        if not backup_path:
            return False, "Nepodařilo se vytvořit zálohu"
        
        try:
            network_type = self.get_network_type()
            interface = config.get("interface", self.get_primary_interface())
            
            log("NETWORK", f"Applying config using {network_type} for {interface}")
            
            if network_type == "dhcpcd":
                success = self._apply_dhcpcd(config, interface)
            elif network_type == "netplan":
                success = self._apply_netplan(config, interface)
            elif network_type == "networkmanager":
                success = self._apply_networkmanager(config, interface)
            else:
                return False, "Nepodporovaný typ síťové konfigurace"
            
            if not success:
                self.restore_backup(backup_path)
                return False, "Nepodařilo se aplikovat konfiguraci"
            
            # Schedule rollback if enabled
            if with_rollback:
                self._pending_backup = backup_path
                self._schedule_rollback()
                return True, f"Konfigurace aplikována. Potvrďte do {self.ROLLBACK_TIMEOUT}s, jinak bude obnovena původní."
            
            return True, "Konfigurace úspěšně aplikována"
            
        except Exception as e:
            log("ERROR", f"Failed to apply network config: {e}")
            self.restore_backup(backup_path)
            return False, f"Chyba: {e}"
    
    def _apply_dhcpcd(self, config: Dict, interface: str) -> bool:
        """Apply configuration using dhcpcd."""
        try:
            # Read current config
            with open(self.DHCPCD_CONF) as f:
                content = f.read()
            
            # Remove existing configuration for this interface
            # Match interface block until next interface or end
            import re
            pattern = rf'\n*# Watchdog.*?\ninterface {interface}\n.*?(?=\ninterface |\n#|\Z)'
            content = re.sub(pattern, '', content, flags=re.DOTALL)
            
            # Also remove any other interface block for this interface
            pattern = rf'\ninterface {interface}\n.*?(?=\ninterface |\Z)'
            content = re.sub(pattern, '', content, flags=re.DOTALL)
            
            # Clean up multiple newlines
            content = re.sub(r'\n{3,}', '\n\n', content)
            
            # Add new configuration if static
            if config.get("mode") == "static":
                cidr = self._netmask_to_cidr(config.get("netmask", "255.255.255.0"))
                static_ip = config.get("static_ip")
                gateway = config.get("gateway")
                dns_servers = config.get("dns_servers", [])
                
                static_config = f"""
# Watchdog static configuration - do not edit manually
interface {interface}
static ip_address={static_ip}/{cidr}
"""
                if gateway:
                    static_config += f"static routers={gateway}\n"
                if dns_servers:
                    static_config += f"static domain_name_servers={' '.join(dns_servers)}\n"
                
                content = content.rstrip() + "\n" + static_config
            
            # Write new config
            with open(self.DHCPCD_CONF, 'w') as f:
                f.write(content)
            
            log("NETWORK", f"Updated dhcpcd.conf for {interface}")
            
            # Apply changes - flush old IP and restart
            return self._apply_network_changes(interface)
            
        except Exception as e:
            log("ERROR", f"Failed to apply dhcpcd config: {e}")
            import traceback
            log("ERROR", traceback.format_exc())
            return False
    
    def _apply_netplan(self, config: Dict, interface: str) -> bool:
        """Apply configuration using netplan."""
        try:
            # Find or create netplan config file
            config_file = os.path.join(self.NETPLAN_DIR, "01-watchdog.yaml")
            
            if config.get("mode") == "static":
                cidr = self._netmask_to_cidr(config.get("netmask", "255.255.255.0"))
                static_ip = config.get("static_ip")
                gateway = config.get("gateway")
                dns_servers = config.get("dns_servers", [])
                
                netplan_config = f"""# Generated by Watchdog
network:
  version: 2
  ethernets:
    {interface}:
      dhcp4: false
      addresses:
        - {static_ip}/{cidr}
      routes:
        - to: default
          via: {gateway}
      nameservers:
        addresses: [{', '.join(dns_servers)}]
"""
            else:
                netplan_config = f"""# Generated by Watchdog
network:
  version: 2
  ethernets:
    {interface}:
      dhcp4: true
"""
            
            with open(config_file, 'w') as f:
                f.write(netplan_config)
            
            os.chmod(config_file, 0o600)
            log("NETWORK", f"Created netplan config: {config_file}")
            
            # Apply netplan
            result = subprocess.run(["netplan", "apply"], capture_output=True, text=True)
            if result.returncode != 0:
                log("ERROR", f"Netplan apply failed: {result.stderr}")
                return False
            
            return True
            
        except Exception as e:
            log("ERROR", f"Failed to apply netplan config: {e}")
            return False
    
    def _apply_networkmanager(self, config: Dict, interface: str) -> bool:
        """Apply configuration using NetworkManager (Trixie+)."""
        try:
            conn_name = f"watchdog-{interface}"
            
            # First, delete existing watchdog connection if exists
            subprocess.run(
                ["nmcli", "connection", "delete", conn_name],
                capture_output=True
            )
            
            if config.get("mode") == "static":
                cidr = self._netmask_to_cidr(config.get("netmask", "255.255.255.0"))
                static_ip = config.get("static_ip")
                gateway = config.get("gateway")
                dns_servers = config.get("dns_servers", [])
                
                # Create new static connection
                cmd = [
                    "nmcli", "connection", "add",
                    "type", "ethernet",
                    "con-name", conn_name,
                    "ifname", interface,
                    "ipv4.method", "manual",
                    "ipv4.addresses", f"{static_ip}/{cidr}",
                    "ipv4.gateway", gateway,
                    "ipv4.dns", ",".join(dns_servers) if dns_servers else "8.8.8.8",
                    "connection.autoconnect", "yes"
                ]
            else:
                # Create DHCP connection
                cmd = [
                    "nmcli", "connection", "add",
                    "type", "ethernet",
                    "con-name", conn_name,
                    "ifname", interface,
                    "ipv4.method", "auto",
                    "connection.autoconnect", "yes"
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                log("ERROR", f"nmcli add failed: {result.stderr}")
                return False
            
            log("NETWORK", f"Created NetworkManager connection: {conn_name}")
            
            # Deactivate any existing connection on interface
            subprocess.run(
                ["nmcli", "device", "disconnect", interface],
                capture_output=True
            )
            time.sleep(1)
            
            # Activate new connection
            result = subprocess.run(
                ["nmcli", "connection", "up", conn_name],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                log("ERROR", f"nmcli up failed: {result.stderr}")
                return False
            
            log("NETWORK", f"Activated connection: {conn_name}")
            
            # Wait for connection
            time.sleep(3)
            
            return True
            
        except Exception as e:
            log("ERROR", f"Failed to apply NetworkManager config: {e}")
            import traceback
            log("ERROR", traceback.format_exc())
            return False
    
    def _apply_network_changes(self, interface: str = None) -> bool:
        """Apply network changes by restarting services."""
        try:
            network_type = self.get_network_type()
            interface = interface or self.get_primary_interface()
            
            if network_type == "dhcpcd":
                # 1. Release DHCP lease for this interface
                log("NETWORK", f"Releasing DHCP lease for {interface}")
                subprocess.run(["dhcpcd", "-k", interface], capture_output=True)
                time.sleep(1)
                
                # 2. Flush all IP addresses from interface
                log("NETWORK", f"Flushing IP addresses from {interface}")
                subprocess.run(["ip", "addr", "flush", "dev", interface], capture_output=True)
                time.sleep(1)
                
                # 3. Restart dhcpcd service to apply new config
                log("NETWORK", "Restarting dhcpcd service")
                result = subprocess.run(["systemctl", "restart", "dhcpcd"], capture_output=True, text=True)
                if result.returncode != 0:
                    log("ERROR", f"dhcpcd restart failed: {result.stderr}")
                
            elif network_type == "netplan":
                # Netplan apply already done in _apply_netplan
                pass
            
            elif network_type == "networkmanager":
                # NetworkManager apply already done in _apply_networkmanager
                pass
            
            # Give network time to come up
            time.sleep(5)
            
            # Verify new IP
            new_config = self.get_current_config()
            log("NETWORK", f"New IP: {new_config.get('ip_address')}")
            
            return True
            
        except Exception as e:
            log("ERROR", f"Failed to apply network changes: {e}")
            import traceback
            log("ERROR", traceback.format_exc())
            return False
    
    def _schedule_rollback(self):
        """Schedule automatic rollback if not confirmed."""
        if self._rollback_timer:
            self._rollback_timer.cancel()
        
        def rollback():
            log("NETWORK", "Rollback timeout - restoring previous configuration")
            if self._pending_backup:
                self.restore_backup(self._pending_backup)
                self._pending_backup = None
        
        self._rollback_timer = threading.Timer(self.ROLLBACK_TIMEOUT, rollback)
        self._rollback_timer.start()
        log("NETWORK", f"Scheduled rollback in {self.ROLLBACK_TIMEOUT}s")
    
    def confirm_config(self) -> bool:
        """Confirm network configuration and cancel rollback."""
        if self._rollback_timer:
            self._rollback_timer.cancel()
            self._rollback_timer = None
            self._pending_backup = None
            log("NETWORK", "Configuration confirmed, rollback cancelled")
            return True
        return False
    
    def cancel_config(self) -> bool:
        """Cancel pending configuration and restore backup."""
        if self._rollback_timer:
            self._rollback_timer.cancel()
            self._rollback_timer = None
        
        if self._pending_backup:
            success = self.restore_backup(self._pending_backup)
            self._pending_backup = None
            return success
        return False
    
    def get_pending_change(self) -> bool:
        """Check if there's a pending configuration change."""
        return self._pending_backup is not None


# Global instance
network_manager = NetworkManager()

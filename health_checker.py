"""
Watchdog v4.3 - Health Checker
==============================
Multi-protocol health checking: ping, HTTP, TCP.
"""

import subprocess
import socket
import time
import re
import threading
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict

from constants import (
    CHECK_TYPE_PING, CHECK_TYPE_HTTP, CHECK_TYPE_TCP,
    DEFAULT_LATENCY_WARNING, DEFAULT_LATENCY_CRITICAL
)
from logger import log


@dataclass
class HealthResult:
    """Result of a health check."""
    target: str
    check_type: str
    success: bool
    latency_ms: float = 0.0
    status_code: int = 0  # For HTTP
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "target": self.target,
            "check_type": self.check_type,
            "success": self.success,
            "latency_ms": round(self.latency_ms, 2),
            "status_code": self.status_code,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


class HealthChecker:
    """Multi-protocol health checker."""
    
    def __init__(self):
        self._results: Dict[str, Dict[str, HealthResult]] = defaultdict(dict)
        self._lock = threading.Lock()
        self.latency_warning = DEFAULT_LATENCY_WARNING
        self.latency_critical = DEFAULT_LATENCY_CRITICAL
    
    def ping(self, host: str, timeout: int = 5, count: int = 1) -> HealthResult:
        """
        Ping a host and return result.
        """
        result = HealthResult(
            target=host,
            check_type=CHECK_TYPE_PING,
            success=False
        )
        
        try:
            # Use system ping command
            cmd = ["ping", "-c", str(count), "-W", str(timeout), host]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
            
            if proc.returncode == 0:
                result.success = True
                # Extract latency from ping output
                match = re.search(r'time[=<](\d+\.?\d*)', proc.stdout)
                if match:
                    result.latency_ms = float(match.group(1))
                
                # Check latency thresholds
                if result.latency_ms >= self.latency_critical:
                    log("WARNING", f"CRITICAL latency for {host}: {result.latency_ms}ms")
                elif result.latency_ms >= self.latency_warning:
                    log("WARNING", f"High latency for {host}: {result.latency_ms}ms")
            else:
                result.error = "Host unreachable"
                
        except subprocess.TimeoutExpired:
            result.error = "Timeout"
        except Exception as e:
            result.error = str(e)
        
        self._store_result(host, result)
        return result
    
    def http_check(self, url: str, timeout: int = 10, expected_code: int = 200) -> HealthResult:
        """
        Check HTTP endpoint.
        """
        # Ensure URL has protocol
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"
        
        result = HealthResult(
            target=url,
            check_type=CHECK_TYPE_HTTP,
            success=False
        )
        
        try:
            import urllib.request
            import ssl
            
            start_time = time.time()
            
            # Create request
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Watchdog-HealthCheck"}
            )
            
            # SSL context that doesn't verify (for self-signed certs)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                result.status_code = response.getcode()
                result.latency_ms = (time.time() - start_time) * 1000
                
                if result.status_code == expected_code:
                    result.success = True
                else:
                    result.error = f"Expected {expected_code}, got {result.status_code}"
                
                # Check latency
                if result.latency_ms >= self.latency_critical:
                    log("WARNING", f"CRITICAL latency for {url}: {result.latency_ms:.0f}ms")
                elif result.latency_ms >= self.latency_warning:
                    log("WARNING", f"High latency for {url}: {result.latency_ms:.0f}ms")
                    
        except urllib.error.HTTPError as e:
            result.status_code = e.code
            result.error = f"HTTP {e.code}"
            result.latency_ms = (time.time() - start_time) * 1000
        except urllib.error.URLError as e:
            result.error = str(e.reason)
        except socket.timeout:
            result.error = "Timeout"
        except Exception as e:
            result.error = str(e)
        
        self._store_result(url, result)
        return result
    
    def tcp_check(self, host: str, port: int, timeout: int = 5) -> HealthResult:
        """
        Check if TCP port is open.
        """
        target = f"{host}:{port}"
        result = HealthResult(
            target=target,
            check_type=CHECK_TYPE_TCP,
            success=False
        )
        
        try:
            start_time = time.time()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            conn_result = sock.connect_ex((host, port))
            result.latency_ms = (time.time() - start_time) * 1000
            
            if conn_result == 0:
                result.success = True
            else:
                result.error = f"Port {port} closed"
            
            sock.close()
            
            # Check latency
            if result.success:
                if result.latency_ms >= self.latency_critical:
                    log("WARNING", f"CRITICAL latency for {target}: {result.latency_ms:.0f}ms")
                elif result.latency_ms >= self.latency_warning:
                    log("WARNING", f"High latency for {target}: {result.latency_ms:.0f}ms")
                    
        except socket.timeout:
            result.error = "Timeout"
        except socket.gaierror:
            result.error = "DNS resolution failed"
        except Exception as e:
            result.error = str(e)
        
        self._store_result(target, result)
        return result
    
    def check_server(self, server: str, check_type: str = CHECK_TYPE_PING, 
                     port: int = 80, http_code: int = 200) -> HealthResult:
        """
        Check a server using specified method.
        """
        if check_type == CHECK_TYPE_HTTP:
            return self.http_check(server, expected_code=http_code)
        elif check_type == CHECK_TYPE_TCP:
            return self.tcp_check(server, port)
        else:
            return self.ping(server)
    
    def check_group(self, servers: List[str], check_type: str = CHECK_TYPE_PING,
                   port: int = 80, require_all: bool = False) -> Tuple[bool, List[HealthResult]]:
        """
        Check multiple servers in a group.
        
        Args:
            servers: List of server addresses
            check_type: Type of check (ping, http, tcp)
            port: Port for TCP/HTTP checks
            require_all: If True, all servers must be up. If False, at least one must be up.
        
        Returns:
            (group_healthy, list_of_results)
        """
        results = []
        
        for server in servers:
            result = self.check_server(server, check_type, port)
            results.append(result)
        
        if require_all:
            # All servers must be healthy
            group_healthy = all(r.success for r in results)
        else:
            # At least one server must be healthy (multi-ping mode)
            group_healthy = any(r.success for r in results)
        
        return group_healthy, results
    
    def _store_result(self, target: str, result: HealthResult):
        """Store result for later retrieval."""
        with self._lock:
            self._results[target][result.check_type] = result
    
    def get_result(self, target: str, check_type: str = CHECK_TYPE_PING) -> Optional[HealthResult]:
        """Get last result for a target."""
        with self._lock:
            return self._results.get(target, {}).get(check_type)
    
    def get_all_results(self) -> Dict[str, Dict[str, Dict]]:
        """Get all results as dict."""
        with self._lock:
            return {
                target: {ct: r.to_dict() for ct, r in checks.items()}
                for target, checks in self._results.items()
            }
    
    def clear_results(self):
        """Clear all stored results."""
        with self._lock:
            self._results.clear()


# Global instance
health_checker = HealthChecker()

"""
Watchdog v3.0 - Email Notifier
==============================
SMTP email notifications for resets and errors.
"""

import smtplib
import ssl
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict, List

from constants import DEFAULT_SMTP_PORT, DEFAULT_SMTP_TIMEOUT
from logger import log


class EmailNotifier:
    """SMTP email notification handler."""
    
    def __init__(self, config: Dict = None):
        self.enabled = False
        self.server = ""
        self.port = DEFAULT_SMTP_PORT
        self.username = ""
        self.password = ""
        self.use_tls = True
        self.from_address = ""
        self.to_addresses: List[str] = []
        self.notify_on_reset = True
        self.notify_on_error = True
        self.timeout = DEFAULT_SMTP_TIMEOUT
        
        if config:
            self.configure(config)
    
    def configure(self, smtp_config: Dict):
        """Configure notifier from config dict."""
        self.enabled = smtp_config.get("enabled", False)
        self.server = smtp_config.get("server", "")
        self.port = smtp_config.get("port", DEFAULT_SMTP_PORT)
        self.username = smtp_config.get("username", "")
        self.password = smtp_config.get("password", "")
        self.use_tls = smtp_config.get("use_tls", True)
        self.from_address = smtp_config.get("from_address", "")
        self.to_addresses = smtp_config.get("to_addresses", [])
        self.notify_on_reset = smtp_config.get("notify_on_reset", True)
        self.notify_on_error = smtp_config.get("notify_on_error", True)
        self.timeout = smtp_config.get("timeout", DEFAULT_SMTP_TIMEOUT)
    
    def test_connection(self) -> tuple:
        """
        Test SMTP connection.
        Returns: (success: bool, message: str)
        """
        if not self.enabled:
            return False, "SMTP not enabled"
        
        if not self.server:
            return False, "SMTP server not configured"
        
        try:
            if self.use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(self.server, self.port, timeout=self.timeout) as smtp:
                    smtp.starttls(context=context)
                    if self.username and self.password:
                        smtp.login(self.username, self.password)
            else:
                with smtplib.SMTP(self.server, self.port, timeout=self.timeout) as smtp:
                    if self.username and self.password:
                        smtp.login(self.username, self.password)
            
            return True, "Connection successful"
        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed"
        except smtplib.SMTPConnectError:
            return False, "Connection refused"
        except TimeoutError:
            return False, "Connection timeout"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def send(self, subject: str, body: str, html: bool = False) -> bool:
        """
        Send email notification.
        Returns True if successful.
        """
        if not self.enabled:
            return False
        
        if not self.server or not self.from_address or not self.to_addresses:
            log("EMAIL", "SMTP not fully configured")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[Watchdog] {subject}"
            msg["From"] = self.from_address
            msg["To"] = ", ".join(self.to_addresses)
            
            if html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))
            
            if self.use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(self.server, self.port, timeout=self.timeout) as smtp:
                    smtp.starttls(context=context)
                    if self.username and self.password:
                        smtp.login(self.username, self.password)
                    smtp.sendmail(self.from_address, self.to_addresses, msg.as_string())
            else:
                with smtplib.SMTP(self.server, self.port, timeout=self.timeout) as smtp:
                    if self.username and self.password:
                        smtp.login(self.username, self.password)
                    smtp.sendmail(self.from_address, self.to_addresses, msg.as_string())
            
            log("EMAIL", f"Notification sent: {subject}")
            return True
            
        except Exception as e:
            log("ERROR", f"Email send failed: {e}")
            return False
    
    def send_async(self, subject: str, body: str, html: bool = False):
        """Send email in background thread."""
        if not self.enabled:
            return
        
        thread = threading.Thread(
            target=self.send,
            args=(subject, body, html),
            daemon=True
        )
        thread.start()
    
    def notify_reset(self, group_name: str, servers: List[str], gpio_pin: int, off_time: int):
        """Send reset notification."""
        if not self.enabled or not self.notify_on_reset:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Stats-only mode (no GPIO)
        if gpio_pin is None:
            subject = f"Server Failure Alert - {group_name}"
            body = f"""Watchdog Server Failure Alert
==============================

Group: {group_name}
Time: {timestamp}
Mode: Stats-only (no power control)

Monitored Servers:
{chr(10).join(f'  - {s}' for s in servers)}

All servers in this group are unreachable.
Note: No power reset configured for this group.

--
Watchdog Monitoring System
"""
            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #ffc107;">⚠️ Server Failure - {group_name}</h2>
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr><td style="padding: 8px; font-weight: bold;">Time:</td><td style="padding: 8px;">{timestamp}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Mode:</td><td style="padding: 8px;">Stats-only (no power control)</td></tr>
    </table>
    <h3>Monitored Servers:</h3>
    <ul>
        {''.join(f'<li>{s}</li>' for s in servers)}
    </ul>
    <p style="color: #666;">All servers unreachable. No power reset configured.</p>
    <hr>
    <p style="font-size: 12px; color: #999;">Watchdog Monitoring System</p>
</body>
</html>
"""
        else:
            subject = f"Power Reset - {group_name}"
            body = f"""Watchdog Power Reset Notification
==================================

Group: {group_name}
Time: {timestamp}
GPIO Pin: {gpio_pin}
Off Time: {off_time}s

Monitored Servers:
{chr(10).join(f'  - {s}' for s in servers)}

All servers in this group were unreachable. Power has been cycled.

--
Watchdog Monitoring System
"""
        
            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #dc3545;">⚡ Power Reset - {group_name}</h2>
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr><td style="padding: 8px; font-weight: bold;">Time:</td><td style="padding: 8px;">{timestamp}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">GPIO Pin:</td><td style="padding: 8px;">{gpio_pin}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Off Time:</td><td style="padding: 8px;">{off_time}s</td></tr>
    </table>
    <h3>Monitored Servers:</h3>
    <ul>
        {''.join(f'<li>{s}</li>' for s in servers)}
    </ul>
    <p style="color: #666;">All servers in this group were unreachable. Power has been cycled.</p>
    <hr>
    <p style="font-size: 12px; color: #999;">Watchdog Monitoring System</p>
</body>
</html>
"""
        
        self.send_async(subject, html_body, html=True)
    
    def notify_error(self, error_type: str, message: str, details: str = ""):
        """Send error notification."""
        if not self.enabled or not self.notify_on_error:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        subject = f"Error - {error_type}"
        body = f"""Watchdog Error Notification
===========================

Type: {error_type}
Time: {timestamp}

Message:
{message}

{f'Details:{chr(10)}{details}' if details else ''}

--
Watchdog Monitoring System
"""
        
        self.send_async(subject, body)
    
    def notify_startup(self, groups_count: int, hostname: str):
        """Send startup notification."""
        if not self.enabled:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        subject = f"System Started - {hostname}"
        body = f"""Watchdog System Started
=======================

Hostname: {hostname}
Time: {timestamp}
Active Groups: {groups_count}

The watchdog monitoring system has been started.

--
Watchdog Monitoring System
"""
        
        self.send_async(subject, body)


# Global notifier instance
_notifier: Optional[EmailNotifier] = None


def get_notifier() -> EmailNotifier:
    """Get or create global notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = EmailNotifier()
    return _notifier


def configure_notifier(smtp_config: Dict):
    """Configure global notifier."""
    get_notifier().configure(smtp_config)


def notification_hook(level: str, message: str):
    """
    Logger hook for automatic notifications.
    Connect to logger: add_notification_hook(notification_hook)
    """
    notifier = get_notifier()
    
    if not notifier.enabled:
        return
    
    # Notify on RESET events
    if level == "RESET" and "Triggering power cut" in message:
        # Parse message for details - simplified version
        notifier.send_async(f"Power Reset", message)
    
    # Notify on ERROR events
    elif level == "ERROR" and notifier.notify_on_error:
        notifier.send_async(f"Error", message)

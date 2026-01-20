"""
Watchdog v4.3 - GitHub Updater
==============================
Check for updates and auto-update from GitHub repository.
"""

import os
import json
import subprocess
import shutil
from datetime import datetime
from typing import Optional, Dict, Tuple

from constants import VERSION, GITHUB_REPO, GITHUB_API_URL, GITHUB_RAW_URL
from logger import log


class GitHubUpdater:
    """Handle GitHub-based updates."""
    
    def __init__(self, install_dir: str = "/opt/watchdog"):
        self.install_dir = install_dir
        self.backup_dir = os.path.join(install_dir, "backups")
        self.current_version = VERSION
    
    def check_for_updates(self) -> Dict:
        """
        Check GitHub for newer version.
        Returns dict with update info.
        """
        result = {
            "current_version": self.current_version,
            "latest_version": None,
            "update_available": False,
            "release_notes": None,
            "release_url": None,
            "error": None,
            "checked_at": datetime.now().isoformat()
        }
        
        try:
            import urllib.request
            import ssl
            
            # Create SSL context
            ctx = ssl.create_default_context()
            
            # Get latest release from GitHub API
            api_url = f"{GITHUB_API_URL}/releases/latest"
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "Watchdog-Updater"}
            )
            
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                data = json.loads(response.read().decode())
                
                latest_version = data.get("tag_name", "").lstrip("v")
                result["latest_version"] = latest_version
                result["release_notes"] = data.get("body", "")
                result["release_url"] = data.get("html_url", "")
                
                # Compare versions
                if latest_version and self._compare_versions(latest_version, self.current_version) > 0:
                    result["update_available"] = True
                    log("UPDATE", f"New version available: v{latest_version}")
                else:
                    log("UPDATE", f"Current version v{self.current_version} is up to date")
                    
        except urllib.error.HTTPError as e:
            if e.code == 404:
                result["error"] = "No releases found on GitHub"
            else:
                result["error"] = f"GitHub API error: {e.code}"
            log("ERROR", f"Update check failed: {result['error']}")
            
        except Exception as e:
            result["error"] = str(e)
            log("ERROR", f"Update check failed: {e}")
        
        return result
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.
        Returns: 1 if v1 > v2, -1 if v1 < v2, 0 if equal
        """
        def normalize(v):
            return [int(x) for x in v.split(".")]
        
        try:
            parts1 = normalize(v1)
            parts2 = normalize(v2)
            
            # Pad shorter version with zeros
            while len(parts1) < len(parts2):
                parts1.append(0)
            while len(parts2) < len(parts1):
                parts2.append(0)
            
            for i in range(len(parts1)):
                if parts1[i] > parts2[i]:
                    return 1
                elif parts1[i] < parts2[i]:
                    return -1
            return 0
        except:
            return 0
    
    def is_git_repo(self) -> bool:
        """Check if install directory is a git repository."""
        return os.path.exists(os.path.join(self.install_dir, ".git"))
    
    def get_git_status(self) -> Dict:
        """Get current git status."""
        result = {
            "is_git_repo": False,
            "branch": None,
            "commit": None,
            "has_changes": False,
            "remote_url": None
        }
        
        if not self.is_git_repo():
            return result
        
        result["is_git_repo"] = True
        
        try:
            # Get current branch
            proc = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.install_dir,
                capture_output=True,
                text=True
            )
            if proc.returncode == 0:
                result["branch"] = proc.stdout.strip()
            
            # Get current commit
            proc = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self.install_dir,
                capture_output=True,
                text=True
            )
            if proc.returncode == 0:
                result["commit"] = proc.stdout.strip()
            
            # Check for local changes (ignore config files)
            proc = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.install_dir,
                capture_output=True,
                text=True
            )
            if proc.returncode == 0:
                # Filter out expected local files
                ignored_patterns = [
                    'config.json', 
                    'users.json', 
                    'log/', 
                    'stats/', 
                    'backups/', 
                    'ssl/',
                    'commands/',
                    'docs/',
                    'schematics/',
                    '.pyc',
                    '__pycache__',
                    '.log',
                    '.stats',
                    '.pem',
                    '.crt',
                    '.key',
                    '.swp',
                    '.tmp'
                ]
                changes = proc.stdout.strip().split('\n') if proc.stdout.strip() else []
                significant_changes = [c for c in changes if c and not any(p in c for p in ignored_patterns)]
                result["has_changes"] = bool(significant_changes)
            
            # Get remote URL
            proc = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.install_dir,
                capture_output=True,
                text=True
            )
            if proc.returncode == 0:
                result["remote_url"] = proc.stdout.strip()
                
        except Exception as e:
            log("ERROR", f"Git status check failed: {e}")
        
        return result
    
    def backup_before_update(self) -> Optional[str]:
        """Create backup before updating."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"pre_update_{timestamp}")
            os.makedirs(backup_path, exist_ok=True)
            
            # Backup critical files
            for filename in ["config.json", "users.json"]:
                src = os.path.join(self.install_dir, filename)
                if os.path.exists(src):
                    shutil.copy2(src, backup_path)
            
            # Backup logs
            log_dir = os.path.join(self.install_dir, "log")
            if os.path.exists(log_dir):
                shutil.copytree(log_dir, os.path.join(backup_path, "log"))
            
            # Backup stats
            stats_dir = os.path.join(self.install_dir, "stats")
            if os.path.exists(stats_dir):
                shutil.copytree(stats_dir, os.path.join(backup_path, "stats"))
            
            log("UPDATE", f"Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            log("ERROR", f"Backup failed: {e}")
            return None
    
    def update_from_git(self) -> Tuple[bool, str]:
        """
        Update from GitHub using git pull.
        Returns (success, message).
        """
        if not self.is_git_repo():
            return False, "Not a git repository. Please reinstall using git clone."
        
        # Create backup first
        backup_path = self.backup_before_update()
        if not backup_path:
            return False, "Failed to create backup"
        
        try:
            # Fix git ownership issue
            subprocess.run(
                ["git", "config", "--global", "--add", "safe.directory", self.install_dir],
                capture_output=True
            )
            
            # Stash any local changes
            subprocess.run(
                ["git", "stash"],
                cwd=self.install_dir,
                capture_output=True
            )
            
            # Fetch latest
            proc = subprocess.run(
                ["git", "fetch", "origin"],
                cwd=self.install_dir,
                capture_output=True,
                text=True
            )
            if proc.returncode != 0:
                return False, f"Git fetch failed: {proc.stderr}"
            
            # Pull changes
            proc = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=self.install_dir,
                capture_output=True,
                text=True
            )
            if proc.returncode != 0:
                return False, f"Git pull failed: {proc.stderr}"
            
            # Restore config files from backup
            for filename in ["config.json", "users.json"]:
                backup_file = os.path.join(backup_path, filename)
                if os.path.exists(backup_file):
                    shutil.copy2(backup_file, os.path.join(self.install_dir, filename))
            
            log("UPDATE", "Git pull successful, config restored")
            return True, "Update successful! Services will restart."
            
        except Exception as e:
            log("ERROR", f"Update failed: {e}")
            return False, str(e)
    
    def restart_services(self) -> bool:
        """Restart watchdog services after update."""
        try:
            subprocess.run(["systemctl", "restart", "watchdog"], capture_output=True)
            subprocess.run(["systemctl", "restart", "watchdog-web"], capture_output=True)
            log("UPDATE", "Services restarted")
            return True
        except Exception as e:
            log("ERROR", f"Service restart failed: {e}")
            return False


# Global instance
updater = GitHubUpdater()

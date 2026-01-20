"""
Watchdog v4.0 - User Management
===============================
Multi-user support with role-based access control.
"""

import json
import os
import secrets
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from werkzeug.security import generate_password_hash, check_password_hash

from constants import (
    USERS_FILE, ROLES, ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER,
    DEFAULT_ADMIN, DEFAULT_LANGUAGE, MAX_USERS
)


class UserManager:
    """Manages users and authentication."""
    
    def __init__(self):
        self._users: Dict[str, dict] = {}
        self._load()
    
    def _load(self):
        """Load users from file."""
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE) as f:
                    data = json.load(f)
                    # Handle both formats: {"users": {...}} and direct {...}
                    if "users" in data:
                        self._users = data["users"]
                    else:
                        self._users = data
            except (json.JSONDecodeError, IOError):
                self._users = {}
        
        # Ensure admin exists
        if not self._users:
            self._create_default_admin()
    
    def _save(self):
        """Save users to file."""
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        # Save with "users" wrapper for consistency
        data = {"users": self._users}
        with open(USERS_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _create_default_admin(self):
        """Create default admin user."""
        self._users["admin"] = {
            **DEFAULT_ADMIN,
            "password_hash": generate_password_hash("admin"),
            "created_at": datetime.now().isoformat(),
            "api_token": None
        }
        self._save()
    
    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """
        Authenticate user.
        Returns user dict if successful, None otherwise.
        """
        user = self._users.get(username)
        if not user:
            return None
        
        if not user.get("active", True):
            return None
        
        if check_password_hash(user.get("password_hash", ""), password):
            # Update last login
            user["last_login"] = datetime.now().isoformat()
            self._save()
            return self.get_user_info(username)
        
        return None
    
    def authenticate_token(self, token: str) -> Optional[dict]:
        """Authenticate via API token."""
        for username, user in self._users.items():
            if user.get("api_token") == token and user.get("active", True):
                return self.get_user_info(username)
        return None
    
    def get_user_info(self, username: str) -> Optional[dict]:
        """Get user info without sensitive data."""
        user = self._users.get(username)
        if not user:
            return None
        
        return {
            "username": username,
            "role": user.get("role", ROLE_VIEWER),
            "language": user.get("language", DEFAULT_LANGUAGE),
            "created_at": user.get("created_at"),
            "last_login": user.get("last_login"),
            "active": user.get("active", True),
            "permissions": self.get_permissions(user.get("role", ROLE_VIEWER))
        }
    
    def get_permissions(self, role: str) -> List[str]:
        """Get permissions for a role."""
        role_info = ROLES.get(role, ROLES[ROLE_VIEWER])
        return role_info.get("permissions", [])
    
    def has_permission(self, username: str, permission: str) -> bool:
        """Check if user has specific permission."""
        user = self.get_user_info(username)
        if not user:
            return False
        return permission in user.get("permissions", [])
    
    def create_user(self, username: str, password: str, role: str = ROLE_VIEWER,
                    language: str = DEFAULT_LANGUAGE) -> Tuple[bool, str]:
        """
        Create new user.
        Returns (success, message).
        """
        if len(self._users) >= MAX_USERS:
            return False, "Maximum number of users reached"
        
        if username in self._users:
            return False, "Username already exists"
        
        if len(username) < 3:
            return False, "Username too short (min 3 chars)"
        
        if len(password) < 4:
            return False, "Password too short (min 4 chars)"
        
        if role not in ROLES:
            return False, "Invalid role"
        
        self._users[username] = {
            "username": username,
            "password_hash": generate_password_hash(password),
            "role": role,
            "language": language,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "active": True,
            "api_token": None
        }
        self._save()
        return True, "User created successfully"
    
    def update_user(self, username: str, **kwargs) -> Tuple[bool, str]:
        """Update user properties."""
        if username not in self._users:
            return False, "User not found"
        
        user = self._users[username]
        
        # Update allowed fields
        if "role" in kwargs and kwargs["role"] in ROLES:
            # Don't allow removing last admin
            if user["role"] == ROLE_ADMIN and kwargs["role"] != ROLE_ADMIN:
                admin_count = sum(1 for u in self._users.values() if u.get("role") == ROLE_ADMIN)
                if admin_count <= 1:
                    return False, "Cannot remove last admin"
            user["role"] = kwargs["role"]
        
        if "language" in kwargs:
            user["language"] = kwargs["language"]
        
        if "active" in kwargs:
            # Don't allow deactivating last admin
            if user["role"] == ROLE_ADMIN and not kwargs["active"]:
                active_admins = sum(1 for u in self._users.values() 
                                   if u.get("role") == ROLE_ADMIN and u.get("active", True))
                if active_admins <= 1:
                    return False, "Cannot deactivate last admin"
            user["active"] = kwargs["active"]
        
        self._save()
        return True, "User updated"
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user's own password."""
        if username not in self._users:
            return False, "User not found"
        
        user = self._users[username]
        
        if not check_password_hash(user.get("password_hash", ""), old_password):
            return False, "Current password is incorrect"
        
        if len(new_password) < 4:
            return False, "New password too short (min 4 chars)"
        
        user["password_hash"] = generate_password_hash(new_password)
        self._save()
        return True, "Password changed"
    
    def reset_password(self, username: str, new_password: str) -> Tuple[bool, str]:
        """Admin reset of user password."""
        if username not in self._users:
            return False, "User not found"
        
        if len(new_password) < 4:
            return False, "Password too short (min 4 chars)"
        
        self._users[username]["password_hash"] = generate_password_hash(new_password)
        self._save()
        return True, "Password reset"
    
    def delete_user(self, username: str) -> Tuple[bool, str]:
        """Delete user."""
        if username not in self._users:
            return False, "User not found"
        
        user = self._users[username]
        
        # Don't allow deleting last admin
        if user.get("role") == ROLE_ADMIN:
            admin_count = sum(1 for u in self._users.values() if u.get("role") == ROLE_ADMIN)
            if admin_count <= 1:
                return False, "Cannot delete last admin"
        
        del self._users[username]
        self._save()
        return True, "User deleted"
    
    def generate_api_token(self, username: str) -> Optional[str]:
        """Generate new API token for user."""
        if username not in self._users:
            return None
        
        token = secrets.token_hex(32)
        self._users[username]["api_token"] = token
        self._save()
        return token
    
    def revoke_api_token(self, username: str) -> bool:
        """Revoke user's API token."""
        if username not in self._users:
            return False
        
        self._users[username]["api_token"] = None
        self._save()
        return True
    
    def list_users(self) -> List[dict]:
        """List all users (without sensitive data)."""
        return [self.get_user_info(username) for username in self._users]
    
    def get_role_name(self, role: str, language: str = "cs") -> str:
        """Get localized role name."""
        role_info = ROLES.get(role, {})
        key = f"name_{language}"
        return role_info.get(key, role_info.get("name_en", role))


# Global instance
user_manager = UserManager()

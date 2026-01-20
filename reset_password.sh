#!/bin/bash
#
# Watchdog v1.0 - Password Reset
#

INSTALL_DIR="/opt/watchdog"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Watchdog Password Reset                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo "Run as root: sudo bash reset_password.sh"
    exit 1
fi

read -p "Username [admin]: " USERNAME
USERNAME=${USERNAME:-admin}

read -s -p "New password: " PASSWORD
echo ""

if [ -z "$PASSWORD" ]; then
    echo "Password cannot be empty!"
    exit 1
fi

python3 << PYEOF
import json
from werkzeug.security import generate_password_hash

try:
    with open("$INSTALL_DIR/users.json", "r") as f:
        data = json.load(f)
    
    # Handle both old and new format
    if "users" in data:
        users = data["users"]
    else:
        users = data
        data = {"users": users}
    
    if "$USERNAME" not in users:
        print("User '$USERNAME' not found!")
        exit(1)
    
    users["$USERNAME"]["password_hash"] = generate_password_hash("$PASSWORD")
    
    with open("$INSTALL_DIR/users.json", "w") as f:
        json.dump(data, f, indent=2)
    
    print("")
    print("Password changed for user: $USERNAME")
    
except Exception as e:
    print(f"Error: {e}")
    exit(1)
PYEOF

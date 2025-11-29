import json
import hashlib
import string
from typing import Optional, Dict, Any, List
from pathlib import Path

# Path to users.json (relative to project root)
USERS_FILE = Path(__file__).parent.parent / "models" / "users.json"


def _ensure_users_file():
    """Ensure the users.json file exists with empty dict"""
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f, indent=2)


def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def _is_hashed_password(value: str) -> bool:
    """Check if a stored password already looks like a SHA-256 hex digest."""
    if not isinstance(value, str) or len(value) != 64:
        return False
    hex_chars = set(string.hexdigits.lower())
    return all(ch in hex_chars for ch in value.lower())


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed


def authenticate(username: str, password: str) -> Optional[Dict[str, str]]:
    """
    Authenticate user credentials.
    Returns user info dict with 'username' and 'role' if successful, None otherwise.
    """
    _ensure_users_file()
    
    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        
        if username in users:
            user_data = users[username]
            stored_password = user_data.get("password", "")
            
            # Only verify using hashed password (no plaintext support)
            if verify_password(password, stored_password):
                return {
                    "username": username,
                    "role": user_data.get("role", "user")
                }
    
    except Exception as e:
        print(f"Error authenticating user: {e}")
    
    return None


def get_all_users() -> Dict[str, Dict[str, str]]:
    """Get all users (admin only)"""
    _ensure_users_file()
    
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading users: {e}")
        return {}


def add_user(username: str, password: str, role: str = "user") -> bool:
    """
    Add a new user.
    Returns True if successful, False if user already exists.
    """
    _ensure_users_file()
    
    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        
        if username in users:
            return False  # User already exists
        
        # Hash password before storing
        users[username] = {
            "password": hash_password(password),
            "role": role
        }
        
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        
        return True
    
    except Exception as e:
        print(f"Error adding user: {e}")
        return False


def update_user_role(username: str, role: str) -> bool:
    """Update user role"""
    _ensure_users_file()
    
    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        
        if username not in users:
            return False
        
        users[username]["role"] = role
        
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        
        return True
    
    except Exception as e:
        print(f"Error updating user role: {e}")
        return False


def delete_user(username: str) -> bool:
    """Delete a user (admin only)"""
    _ensure_users_file()
    
    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        
        if username not in users:
            return False
        
        # Prevent deleting the last admin
        admin_count = sum(1 for u in users.values() if u.get("role") == "admin")
        if users[username].get("role") == "admin" and admin_count == 1:
            return False
        
        del users[username]
        
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        
        return True
    
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False


def has_admin_user() -> bool:
    """Check if at least one admin user exists"""
    _ensure_users_file()
    
    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        
        return any(u.get("role") == "admin" for u in users.values())
    except Exception as e:
        print(f"Error checking admin users: {e}")
        return False


def user_exists(username: str) -> bool:
    """Check if a username already exists"""
    _ensure_users_file()
    
    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        return username in users
    except Exception as e:
        print(f"Error checking user existence: {e}")
        return False


def ensure_secure_password_storage() -> List[str]:
    """
    Ensure all stored passwords are hashed.
    Returns list of usernames that were migrated from plaintext.
    """
    _ensure_users_file()

    migrated_users: List[str] = []
    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)

        updated = False
        for username, data in users.items():
            stored_password = data.get("password", "")
            if stored_password and not _is_hashed_password(stored_password):
                users[username]["password"] = hash_password(stored_password)
                migrated_users.append(username)
                updated = True

        if updated:
            with open(USERS_FILE, 'w') as f:
                json.dump(users, f, indent=2)

    except Exception as e:
        print(f"Error securing passwords: {e}")

    return migrated_users


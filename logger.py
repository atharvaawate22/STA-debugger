import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Path to logs.json (relative to project root)
LOGS_FILE = Path(__file__).parent / "models" / "logs.json"


def _ensure_logs_file():
    """Ensure the logs.json file exists"""
    LOGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LOGS_FILE.exists():
        with open(LOGS_FILE, 'w') as f:
            json.dump([], f, indent=2)


def log_action(username: str, action: str, details: Dict[str, Any] = None):
    """
    Log a user action.
    
    Args:
        username: Username of the user performing the action
        action: Description of the action (e.g., "Run STA Analysis", "Generate Summary")
        details: Optional additional details about the action
    """
    _ensure_logs_file()
    
    try:
        # Read existing logs
        with open(LOGS_FILE, 'r') as f:
            logs = json.load(f)
        
        # Create new log entry
        log_entry = {
            "username": username,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        logs.append(log_entry)
        
        # Write back to file
        with open(LOGS_FILE, 'w') as f:
            json.dump(logs, f, indent=2)
    
    except Exception as e:
        print(f"Error logging action: {e}")


def get_all_logs() -> list:
    """Get all logs (admin only)"""
    _ensure_logs_file()
    
    try:
        with open(LOGS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading logs: {e}")
        return []


def get_user_logs(username: str) -> list:
    """Get logs for a specific user"""
    all_logs = get_all_logs()
    return [log for log in all_logs if log.get("username") == username]


def clear_logs() -> bool:
    """Clear all logs (admin only)"""
    _ensure_logs_file()
    
    try:
        with open(LOGS_FILE, 'w') as f:
            json.dump([], f, indent=2)
        return True
    except Exception as e:
        print(f"Error clearing logs: {e}")
        return False


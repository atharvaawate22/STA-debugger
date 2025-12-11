import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Path to api_keys.json (relative to project root)
API_KEYS_FILE = Path(__file__).parent.parent / "models" / "api_keys.json"


def _ensure_api_keys_file():
    """Ensure the api_keys.json file exists with empty array"""
    API_KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not API_KEYS_FILE.exists():
        with open(API_KEYS_FILE, 'w') as f:
            json.dump([], f, indent=2)


def get_all_api_keys() -> List[Dict[str, Any]]:
    """Get all API keys"""
    _ensure_api_keys_file()
    
    try:
        with open(API_KEYS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading API keys: {e}")
        return []


def get_api_key_by_id(api_key_id: str) -> Optional[str]:
    """Get the actual API key value by its ID"""
    keys = get_all_api_keys()
    for key_entry in keys:
        if key_entry.get("id") == api_key_id:
            return key_entry.get("key")
    return None


def add_api_key(name: str, key: str, created_by: str) -> Optional[str]:
    """
    Add a new API key.
    Returns the API key ID if successful, None otherwise.
    """
    _ensure_api_keys_file()
    
    try:
        keys = get_all_api_keys()
        
        # Generate unique ID
        api_key_id = uuid.uuid4().hex
        
        new_key = {
            "id": api_key_id,
            "name": name,
            "key": key,
            "created_by": created_by,
            "created_at": datetime.now().isoformat()
        }
        
        keys.append(new_key)
        
        with open(API_KEYS_FILE, 'w') as f:
            json.dump(keys, f, indent=2)
        
        return api_key_id
    
    except Exception as e:
        print(f"Error adding API key: {e}")
        return None


def delete_api_key(api_key_id: str) -> bool:
    """Delete an API key by ID"""
    _ensure_api_keys_file()
    
    try:
        keys = get_all_api_keys()
        keys = [k for k in keys if k.get("id") != api_key_id]
        
        with open(API_KEYS_FILE, 'w') as f:
            json.dump(keys, f, indent=2)
        
        return True
    
    except Exception as e:
        print(f"Error deleting API key: {e}")
        return False


def mask_api_key(key: str) -> str:
    """Mask API key for display (show first 4 and last 4 chars)"""
    if not key or len(key) < 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def get_api_keys_for_dropdown() -> List[Dict[str, str]]:
    """
    Get API keys formatted for dropdown selection.
    Returns list of dicts with 'id', 'label', and 'masked' keys.
    """
    keys = get_all_api_keys()
    result = []
    for key_entry in keys:
        result.append({
            "id": key_entry.get("id", ""),
            "label": f"{key_entry.get('name', 'Unnamed')} ({mask_api_key(key_entry.get('key', ''))})",
            "masked": mask_api_key(key_entry.get("key", ""))
        })
    return result


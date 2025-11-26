import json
from pathlib import Path
from typing import Optional

# Path to api_config.json (relative to project root)
API_CONFIG_FILE = Path(__file__).parent / "models" / "api_config.json"


def _ensure_api_config_file():
    """Ensure the api_config.json file exists"""
    API_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not API_CONFIG_FILE.exists():
        default_config = {"api_key": ""}
        with open(API_CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=2)


def get_api_key() -> Optional[str]:
    """Get the stored API key"""
    _ensure_api_config_file()
    
    try:
        with open(API_CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get("api_key", "") or None
    except Exception as e:
        print(f"Error reading API key: {e}")
        return None


def set_api_key(api_key: str) -> bool:
    """Set the API key"""
    _ensure_api_config_file()
    
    try:
        config = {"api_key": api_key}
        with open(API_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error setting API key: {e}")
        return False


def has_api_key() -> bool:
    """Check if API key is set"""
    api_key = get_api_key()
    return api_key is not None and api_key.strip() != ""


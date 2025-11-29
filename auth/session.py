import streamlit as st
from typing import Optional, Dict, Any


def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current logged-in user info from session state."""
    if st.session_state.get("authenticated") and isinstance(st.session_state.get("user"), dict):
        return st.session_state["user"]
    return None


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return st.session_state.get("authenticated", False)


def is_admin() -> bool:
    """Check if current user is an admin."""
    current_user = get_current_user()
    return bool(current_user and current_user.get("role") == "admin")


def login_user(username: str, role: str):
    """Set user as logged in."""
    st.session_state["authenticated"] = True
    st.session_state["user"] = {
        "username": username,
        "role": role
    }


def logout_user():
    """Log out current user."""
    st.session_state["authenticated"] = False
    st.session_state.pop("user", None)
    st.session_state.pop("selected_api_key_id", None)


import streamlit as st
from app.ui import main_ui
from app.admin_ui import admin_menu
from auth.user_manager import (
    authenticate,
    add_user,
    has_admin_user,
    user_exists,
    ensure_secure_password_storage,
)
from auth.session import login_user, logout_user, get_current_user, is_authenticated
from core.logger import log_action, get_user_logs

# Page configuration
st.set_page_config(
    page_title="GenAI Timing Violation Debugger",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .violation-card {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    .success-card {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)


def show_create_admin():
    """Display initial admin creation screen"""
    st.markdown("<h1 style='text-align: center; color: #1e77b4; font-size: 2.5rem; margin-bottom: 1rem;'>GenAI Timing Violation Debugger</h1>", 
                unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #666; font-size: 1.5rem; margin-bottom: 2rem;'>AI-powered analysis for semiconductor timing closure</h3>",
                unsafe_allow_html=True)
    
    st.divider()
    st.info("👋 Welcome! This is the first run. Please create an admin account to get started.")
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("🔐 Create Admin Account")
            
            with st.form("create_admin_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Create Admin", type="primary")
                
                if submitted:
                    if not username or not password:
                        st.error("❌ Please enter both username and password.")
                    elif password != confirm_password:
                        st.error("❌ Passwords do not match.")
                    elif user_exists(username):
                        st.error("❌ Username already exists.")
                    else:
                        if add_user(username, password, role="admin"):
                            st.success(f"✅ Admin account '{username}' created successfully!")
                            log_action(username, "Admin Account Created", details={"action": "initial_setup"})
                            st.info("Please refresh the page to login.")
                            st.rerun()
                        else:
                            st.error("❌ Failed to create admin account. Please try again.")


def show_login():
    """Display login form"""
   st.markdown("<h1 style='text-align: center; color: #1e77b4; font-size: 2.5rem; margin-bottom: 1rem;'>GenAI Timing Violation Debugger</h1>", 
                unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #666; font-size: 1.5rem; margin-bottom: 2rem;'>AI-powered analysis for semiconductor timing closure</h3>",
                unsafe_allow_html=True)
    
    st.divider()
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("🔐 Login")
            
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", type="primary")
                
                if submitted:
                    if username and password:
                        user_info = authenticate(username, password)
                        if user_info:
                            login_user(user_info["username"], user_info["role"])
                            log_action(username, "Login Success", details={})
                            st.success(f"✅ Welcome, {username}!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid username or password.")
                            log_action(username, "Login Failed", details={"reason": "invalid_credentials"})
                    else:
                        st.error("❌ Please enter both username and password.")
            
            st.divider()
            st.markdown("### Don't have an account?")
            if st.button("Register", use_container_width=True):
                st.session_state["show_register"] = True
                st.rerun()


def show_register():
    """Display registration form"""
    st.markdown("<h1 style='text-align: center; color: #1e77b4; font-size: 2.5rem; margin-bottom: 1rem;'>GenAI Timing Violation Debugger</h1>", 
                unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #666; font-size: 1.5rem; margin-bottom: 2rem;'>AI-powered analysis for semiconductor timing closure</h3>",
                unsafe_allow_html=True)
    
    st.divider()
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("📝 Register New Account")
            
            with st.form("register_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Register", type="primary")
                
                if submitted:
                    if not username or not password:
                        st.error("❌ Please enter both username and password.")
                    elif password != confirm_password:
                        st.error("❌ Passwords do not match.")
                    elif user_exists(username):
                        st.error("❌ Username already exists. Please choose a different username.")
                    else:
                        if add_user(username, password, role="user"):
                            st.success(f"✅ Account '{username}' created successfully!")
                            log_action(username, "User Registration", details={})
                            st.info("You can now login with your credentials.")
                            st.session_state["show_register"] = False
                            st.rerun()
                        else:
                            st.error("❌ Failed to create account. Please try again.")
            
            st.divider()
            if st.button("Back to Login", use_container_width=True):
                st.session_state["show_register"] = False
                st.rerun()


def show_user_ui():
    """Show user interface with optional log viewing"""
    st.sidebar.header("👤 User Menu")
    
    view_option = st.sidebar.radio(
        "Menu",
        ["STA Tool", "My Logs"],
        key="user_menu_option"
    )
    
    if view_option == "My Logs":
        st.header("📋 My Activity Logs")
        user = get_current_user() or {}
        username = user.get("username", "Unknown")
        logs = get_user_logs(username)
        
        if logs:
            # Sort by timestamp (newest first)
            logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            st.metric("Total Log Entries", len(logs))
            
            for log in logs:
                with st.expander(f"[{log.get('timestamp', 'Unknown time')}] {log.get('action', 'Unknown action')}"):
                    st.json(log)
        else:
            st.info("No activity logs found.")
    else:
        main_ui()


def _initialize_security_flags():
    """Run password hardening and prime any warning banners."""
    migrated_users = ensure_secure_password_storage()
    if migrated_users:
        existing = st.session_state.get("password_reset_notice_users", [])
        notice_set = {user for user in existing if user}
        notice_set.update(migrated_users)
        st.session_state["password_reset_notice_users"] = sorted(notice_set)


def _show_password_reset_notice(role: str):
    """Warn admins if auto-migrated plaintext passwords were detected."""
    if role != "admin":
        return

    insecure_users = st.session_state.get("password_reset_notice_users", [])
    if not insecure_users:
        return

    with st.expander("⚠️ Password reset recommended", expanded=True):
        st.warning(
            "We detected legacy plaintext passwords and auto-hardened them. "
            "Please reset the following accounts to ensure users know their updated credentials:\n"
            f"• {', '.join(insecure_users)}"
        )
        if st.button("Dismiss warning", key="dismiss_password_notice"):
            st.session_state["password_reset_notice_users"] = []
            st.rerun()


def main():
    """Main application entry point with authentication"""
    _initialize_security_flags()

    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "show_register" not in st.session_state:
        st.session_state["show_register"] = False
    
    # Check if admin exists
    if not has_admin_user():
        # Show create admin screen
        show_create_admin()
        return
    
    # Check authentication
    if not is_authenticated():
        # Show register or login
        if st.session_state.get("show_register", False):
            show_register()
        else:
            show_login()
    else:
        # User is authenticated
        user = get_current_user() or {}
        username = user.get("username", "Unknown")
        role = user.get("role", "user")

        _show_password_reset_notice(role)
        
        # Logout button in sidebar
        if st.sidebar.button("🚪 Logout"):
            log_action(username, "Logout", details={})
            logout_user()
            st.rerun()
        
        st.sidebar.info(f"Logged in as: **{username}** ({role})")
        
        # Route based on role
        if role == "admin":
            # Admin can switch between admin panel and STA tool
            admin_view = st.sidebar.radio(
                "Admin View",
                ["Admin Panel", "STA Tool"],
                key="admin_view_option"
            )
            
            if admin_view == "Admin Panel":
                admin_menu(username)
            else:
                st.markdown('<h1 class="main-header">⚡ GenAI Timing Violation Debugger</h1>', unsafe_allow_html=True)
                st.markdown("### AI-powered analysis for semiconductor timing closure")
                main_ui()
        else:
            # Regular user
            st.markdown('<h1 class="main-header">⚡ GenAI Timing Violation Debugger</h1>', unsafe_allow_html=True)
            st.markdown("### AI-powered analysis for semiconductor timing closure")
            show_user_ui()


if __name__ == "__main__":
    main()

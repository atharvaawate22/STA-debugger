import streamlit as st
from app.ui import main_ui
from app.admin_ui import admin_menu
from auth.user_manager import authenticate
from logger import get_user_logs

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


def show_login():
    """Display login form"""
    st.markdown('<h1 class="main-header">⚡ GenAI Timing Violation Debugger</h1>', unsafe_allow_html=True)
    st.markdown("### AI-powered analysis for semiconductor timing closure")
    
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
                            st.session_state["authenticated"] = True
                            st.session_state["username"] = user_info["username"]
                            st.session_state["role"] = user_info["role"]
                            st.success(f"✅ Welcome, {username}!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid username or password.")
                    else:
                        st.error("❌ Please enter both username and password.")


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
        username = st.session_state.get("username", "Unknown")
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


def main():
    """Main application entry point with authentication"""
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    # Check authentication
    if not st.session_state.get("authenticated", False):
        show_login()
    else:
        # User is authenticated
        username = st.session_state.get("username", "Unknown")
        role = st.session_state.get("role", "user")
        
        # Logout button in sidebar
        if st.sidebar.button("🚪 Logout"):
            st.session_state["authenticated"] = False
            st.session_state["username"] = None
            st.session_state["role"] = None
            st.session_state["view_logs"] = False
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
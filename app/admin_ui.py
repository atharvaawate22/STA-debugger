import streamlit as st
import json
from auth.user_manager import (
    authenticate, add_user, get_all_users, delete_user
)
from api_manager import set_api_key, get_api_key, has_api_key
from logger import get_all_logs, get_user_logs


def admin_menu(username: str):
    """Display admin menu and handle admin actions"""
    menu_option = st.sidebar.selectbox(
        "Admin Menu",
        ["Dashboard", "Manage API Key", "Manage Users", "View Activity Logs"],
        key="admin_menu"
    )
    
    if menu_option == "Dashboard":
        show_admin_dashboard()
    elif menu_option == "Manage API Key":
        manage_api_key()
    elif menu_option == "Manage Users":
        manage_users()
    elif menu_option == "View Activity Logs":
        view_activity_logs()


def show_admin_dashboard():
    """Show admin dashboard with overview"""
    st.header("📊 Admin Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        users = get_all_users()
        st.metric("Total Users", len(users))
    
    with col2:
        api_configured = "✅ Configured" if has_api_key() else "❌ Not Set"
        st.metric("API Key Status", api_configured)
    
    with col3:
        logs = get_all_logs()
        st.metric("Total Log Entries", len(logs))
    
    st.info("💡 Use the sidebar menu to manage API keys, users, and view activity logs.")


def manage_api_key():
    """Allow admin to set or update API key"""
    st.header("🔑 Manage API Key")
    
    current_key = get_api_key()
    
    if current_key:
        st.info(f"✅ API key is currently set: {current_key[:8]}...{current_key[-4:]}")
        if st.button("Show Full Key"):
            st.code(current_key)
    else:
        st.warning("❌ No API key is currently set. Please set one to enable STA analysis.")
    
    st.subheader("Set/Update API Key")
    new_key = st.text_input(
        "Groq API Key",
        type="password",
        help="Enter the Groq API key for the organization"
    )
    
    if st.button("Save API Key", type="primary"):
        if new_key and new_key.strip():
            if set_api_key(new_key.strip()):
                st.success("✅ API key saved successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to save API key. Please try again.")
        else:
            st.error("❌ Please enter a valid API key.")


def manage_users():
    """Allow admin to add, view, and delete users"""
    st.header("👥 Manage Users")
    
    # Add new user
    st.subheader("Add New User")
    with st.form("add_user_form"):
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        new_role = st.selectbox("Role", ["user", "admin"])
        
        submitted = st.form_submit_button("Add User", type="primary")
        if submitted:
            if new_username and new_password:
                if add_user(new_username, new_password, new_role):
                    st.success(f"✅ User '{new_username}' added successfully!")
                    st.rerun()
                else:
                    st.error(f"❌ User '{new_username}' already exists.")
            else:
                st.error("❌ Please provide both username and password.")
    
    st.divider()
    
    # List all users
    st.subheader("Current Users")
    users = get_all_users()
    
    if users:
        user_data = []
        for username, user_info in users.items():
            user_data.append({
                "Username": username,
                "Role": user_info.get("role", "user"),
                "Actions": username
            })
        
        import pandas as pd
        df = pd.DataFrame(user_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Delete user option
        st.subheader("Delete User")
        usernames_to_delete = [u for u in users.keys()]
        if usernames_to_delete:
            user_to_delete = st.selectbox("Select user to delete", usernames_to_delete)
            if st.button("Delete User", type="secondary"):
                if delete_user(user_to_delete):
                    st.success(f"✅ User '{user_to_delete}' deleted successfully!")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to delete user '{user_to_delete}'. Cannot delete the last admin.")
    else:
        st.info("No users found.")


def view_activity_logs():
    """Display activity logs"""
    st.header("📋 Activity Logs")
    
    logs = get_all_logs()
    
    if not logs:
        st.info("No activity logs found.")
        return
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        filter_user = st.selectbox(
            "Filter by User",
            ["All"] + list(set(log.get("username", "Unknown") for log in logs))
        )
    
    # Filter logs
    filtered_logs = logs
    if filter_user != "All":
        filtered_logs = [log for log in logs if log.get("username") == filter_user]
    
    # Sort by timestamp (newest first)
    filtered_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    st.metric("Total Log Entries", len(filtered_logs))
    
    # Display logs
    for log in filtered_logs:
        with st.expander(f"[{log.get('timestamp', 'Unknown time')}] {log.get('username', 'Unknown')} - {log.get('action', 'Unknown action')}"):
            st.json(log)


import streamlit as st
import json
from auth.user_manager import (
    add_user, get_all_users, delete_user, update_user_role, user_exists
)
from core.api_manager import (
    get_all_api_keys, add_api_key, delete_api_key, 
    mask_api_key, get_api_keys_for_dropdown
)
from core.logger import get_all_logs, get_user_logs, log_action


def admin_menu(username: str):
    """Display admin menu and handle admin actions"""
    menu_option = st.sidebar.selectbox(
        "Admin Menu",
        ["Dashboard", "Manage API Keys", "Manage Users", "View Activity Logs"],
        key="admin_menu"
    )
    
    if menu_option == "Dashboard":
        show_admin_dashboard()
    elif menu_option == "Manage API Keys":
        manage_api_keys(username)
    elif menu_option == "Manage Users":
        manage_users(username)
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
        api_keys = get_all_api_keys()
        st.metric("API Keys", len(api_keys))
    
    with col3:
        logs = get_all_logs()
        st.metric("Total Log Entries", len(logs))
    
    st.info("💡 Use the sidebar menu to manage API keys, users, and view activity logs.")


def manage_api_keys(username: str):
    """Allow admin to add, view, and remove API keys"""
    st.header("🔑 Manage API Keys")
    
    # Add new API key
    st.subheader("Add New API Key")
    with st.form("add_api_key_form"):
        key_name = st.text_input("API Key Name/Label", help="A descriptive name for this API key")
        api_key = st.text_input(
            "API Key",
            type="password",
            help="Enter the Groq API key"
        )
        
        submitted = st.form_submit_button("Add API Key", type="primary")
        if submitted:
            if key_name and api_key and api_key.strip():
                api_key_id = add_api_key(key_name.strip(), api_key.strip(), username)
                if api_key_id:
                    st.success(f"✅ API key '{key_name}' added successfully!")
                    log_action(
                        username,
                        "Add API Key",
                        api_key_id=api_key_id,
                        details={"key_name": key_name},
                    )
                    st.rerun()
                else:
                    st.error("❌ Failed to add API key. Please try again.")
            else:
                st.error("❌ Please provide both name and API key.")
    
    st.divider()
    
    # List all API keys
    st.subheader("Current API Keys")
    api_keys = get_all_api_keys()
    
    if api_keys:
        # Display keys in a table
        key_data = []
        for key_entry in api_keys:
            key_data.append({
                "Name": key_entry.get("name", "Unnamed"),
                "Masked Key": mask_api_key(key_entry.get("key", "")),
                "Created By": key_entry.get("created_by", "Unknown"),
                "Created At": key_entry.get("created_at", "Unknown"),
                "ID": key_entry.get("id", "")
            })
        
        import pandas as pd
        df = pd.DataFrame(key_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Delete API key option
        st.subheader("Delete API Key")
        key_options = {f"{k.get('name', 'Unnamed')} ({mask_api_key(k.get('key', ''))})": k.get("id") 
                      for k in api_keys}
        
        if key_options:
            selected_key_label = st.selectbox("Select API key to delete", list(key_options.keys()))
            if st.button("Delete API Key", type="secondary"):
                key_id_to_delete = key_options[selected_key_label]
                if delete_api_key(key_id_to_delete):
                    st.success(f"✅ API key deleted successfully!")
                    log_action(
                        username,
                        "Delete API Key",
                        api_key_id=key_id_to_delete,
                        details={},
                    )
                    st.rerun()
                else:
                    st.error("❌ Failed to delete API key. Please try again.")
    else:
        st.info("No API keys found. Add one above to get started.")


def manage_users(username: str):
    """Allow admin to add, view, delete, and manage user roles"""
    st.header("👥 Manage Users")
    
    # Add new user
    st.subheader("Add New User")
    with st.form("add_user_form"):
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        new_role = st.selectbox("Role", ["user", "admin"])
        
        submitted = st.form_submit_button("Add User", type="primary")
        if submitted:
            if new_username and new_password:
                if new_password != confirm_password:
                    st.error("❌ Passwords do not match.")
                elif user_exists(new_username):
                    st.error(f"❌ User '{new_username}' already exists.")
                elif add_user(new_username, new_password, new_role):
                    st.success(f"✅ User '{new_username}' added successfully!")
                    log_action(username, "Add User", details={"new_username": new_username, "role": new_role})
                    st.rerun()
                else:
                    st.error(f"❌ Failed to add user '{new_username}'.")
            else:
                st.error("❌ Please provide both username and password.")
    
    st.divider()
    
    # List all users
    st.subheader("Current Users")
    users = get_all_users()
    
    if users:
        user_data = []
        for username_key, user_info in users.items():
            user_data.append({
                "Username": username_key,
                "Role": user_info.get("role", "user"),
                "Actions": username_key
            })
        
        import pandas as pd
        df = pd.DataFrame(user_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Manage user roles and deletion
        st.subheader("Manage User")
        usernames_list = list(users.keys())
        if usernames_list:
            user_to_manage = st.selectbox("Select user to manage", usernames_list)
            current_role = users[user_to_manage].get("role", "user")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Current Role:** {current_role}")
                new_role = st.selectbox(
                    "Change Role",
                    ["user", "admin"],
                    index=0 if current_role == "user" else 1,
                    key=f"role_{user_to_manage}"
                )
                if new_role != current_role:
                    if st.button("Update Role", key=f"update_{user_to_manage}"):
                        if update_user_role(user_to_manage, new_role):
                            st.success(f"✅ Role updated to {new_role}!")
                            log_action(username, "Update User Role", details={
                                "target_user": user_to_manage,
                                "new_role": new_role,
                                "old_role": current_role
                            })
                            st.rerun()
                        else:
                            st.error("❌ Failed to update role.")
            
            with col2:
                st.write("**Delete User**")
                if user_to_manage == username:
                    st.warning("⚠️ You cannot delete your own account.")
                else:
                    if st.button("Delete User", type="secondary", key=f"delete_{user_to_manage}"):
                        if delete_user(user_to_manage):
                            st.success(f"✅ User '{user_to_manage}' deleted successfully!")
                            log_action(username, "Delete User", details={"deleted_user": user_to_manage})
                            st.rerun()
                        else:
                            st.error(f"❌ Cannot delete user '{user_to_manage}'. Cannot delete the last admin.")
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
            ["All"] + sorted(list(set(log.get("username", "Unknown") for log in logs)))
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
        api_key_info = ""
        if log.get("api_key_id"):
            api_key_info = f" [API Key: {log.get('api_key_id')[:8]}...]"
        
        with st.expander(f"[{log.get('timestamp', 'Unknown time')}] {log.get('username', 'Unknown')} - {log.get('action', 'Unknown action')}{api_key_info}"):
            st.json(log)

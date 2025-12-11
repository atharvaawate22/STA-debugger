# ⚡ GenAI-Powered STA Debugger

**AI-powered analysis for semiconductor timing closure**

---

## 🚀 Overview

The **STA Debugger** is a **web-based AI tool** that automates the analysis of Static Timing Analysis (STA) reports, identifies timing violations, and provides **expert-level recommendations** to help engineers achieve faster timing closure.

It is designed to simplify one of the most time-consuming stages in chip design — **debugging STA reports** — by combining the analytical accuracy of open-source EDA tools like **OpenSTA** with the intelligence of **Generative AI (Groq API)**.

The platform features a **Streamlit-based interface** for ease of use and generates detailed reports in both **JSON** and **PDF** formats.

---

## 👨‍💻 Team
- **Tushar Bhandari** — Machine Learning & Backend Development  
- **Atharva Awate** — Frontend and System Integration  
- **Yash Pahade** — Data Analysis & Report Generation  

---

## ✨ Features

- **AI-Powered Analysis**  
  Provides in-depth reasoning, root causes, severity level, and precise design-level fixes for each timing violation using **Groq’s LLM** (`llama-3.3-70b-versatile`).

- **Interactive Web Interface**  
  A simple, elegant UI built with **Streamlit** for uploading reports, configuring analysis options, and reviewing AI-generated results.

- **Report Generation**  
  Download complete results in both **JSON** and **PDF** formats for easy documentation and sharing.

- **Support for Standard STA Formats**  
  Compatible with industry-standard reports generated from tools like **OpenSTA**.

- **Fast and Insightful**  
  Saves hours of manual debugging by providing immediate actionable insights and structured timing violation analysis.

---

## 🧠 How It Works

The STA Debugger follows a simple 5-step workflow:

1. **Upload Report**  
   Upload an STA timing report (`.txt`, `.rpt`, or `.log`).

2. **Parse Report**  
   A custom `STAParser` extracts critical timing information such as start points, endpoints, logic chains, and slack.

3. **AI Analysis (Groq API)**  
   Parsed data is sent to **Groq’s LLM** for quantitative reasoning, cause identification, and optimization suggestions.

4. **Review Results**  
   Results are displayed in an expandable web dashboard showing path-level insights and violation categories.

5. **Export Reports**  
   Download full analysis reports in **JSON** or **PDF** format.

---

## 📋 How to Use This Tool

1. **Get an API Key:**  
   Sign up at [Groq Console](https://console.groq.com/) for free access to the Groq API.

2. **Upload Report:**  
   Upload your STA timing report (`.txt`, `.rpt`, or `.log`).

3. **Configure Options:**  
   Choose analysis options in the sidebar (e.g., analyze only violated paths).

4. **Analyze:**  
   Click **“Run Analysis”** to start AI-powered debugging.

5. **Review Results:**  
   Examine detailed AI insights and recommendations for each timing path.

6. **Export:**  
   Download comprehensive reports in **JSON** or **PDF** formats.

---

## ⚙️ Installation & Setup

### 🧩 Prerequisites
- Python 3.8+  
- Groq API Key (required for AI analysis)  
- Internet connection for Streamlit frontend and API inference

### 🛠️ Installation

Clone the repository:
```bash
git clone https://github.com/Atharva12210985/AI-Powered-Static-Timing-Violation-Debugger-.git
cd AI-Powered-Static-Timing-Violation-Debugger-
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the application:
```bash
streamlit run streamlit_app.py
```

---

## 🧪 Manual Testing Guide

### First Run: Create Admin Account

1. **Start the application** - If `models/users.json` is empty or doesn't exist, you'll see the "Create Admin" screen.
2. **Create admin account** - Enter username, password, and confirm password.
3. **Verify** - After creation, the app should redirect to login screen.

### Admin: Add API Key

1. **Login as admin** - Use the admin credentials you just created.
2. **Navigate to Admin Panel** - Select "Admin Panel" from the sidebar.
3. **Go to "Manage API Keys"** - Click on "Manage API Keys" in the admin menu.
4. **Add API key** - Enter a name/label and the actual Groq API key, then click "Add API Key".
5. **Verify** - The API key should appear in the list with masked display (first 4 and last 4 characters visible).

### Register Regular User

1. **From login screen** - Click "Register" button.
2. **Fill registration form** - Enter username, password, and confirm password.
3. **Submit** - User account should be created successfully.
4. **Verify** - You should be able to login with the new credentials.

### User Login: Select API Key from Dropdown

1. **Login as regular user** - Use the user credentials you created.
2. **Navigate to STA Tool** - The main interface should load.
3. **Check sidebar** - You should see a dropdown labeled "Select API Key" (NOT a text input field).
4. **Select API key** - Choose an API key from the dropdown (shows name and masked key).
5. **Verify** - The selected key should show as "✅ API key selected" with masked display.

### Run STA Action and Check Logs

1. **Upload timing report** - Upload a `.txt`, `.rpt`, or `.log` file in the sidebar.
2. **Run analysis** - Click "Run Analysis" button.
3. **Verify logs** - 
   - As user: Go to "My Logs" in sidebar to see your activity.
   - As admin: Go to "View Activity Logs" to see all user activities.
4. **Check log entries** - Logs should include:
   - Username
   - Action (e.g., "Run STA Analysis", "Login Success")
   - Timestamp (ISO format)
   - API key ID (if an API key was used)
   - Additional details

### Additional Admin Tests

1. **Manage Users** - Add, delete, and change user roles (promote/demote admin).
2. **Delete API Key** - Remove an API key and verify it's removed from dropdown.
3. **View Activity Logs** - Filter logs by user and verify all actions are logged.

---

### Quick Verification Checklist
1. Launch the app with empty `models/users.json` and create the first admin.
2. As admin, add at least one API key from **Manage API Keys**.
3. Register a new regular user via the Login → Register flow (or add via Admin UI).
4. Log in as that user and confirm the sidebar shows only the API key dropdown (no text input).
5. Upload a timing report, run STA analysis, then confirm a new log entry appears for both the user and in the admin Activity Logs view.

## 🔒 Security Features

- **Password Hashing**: All passwords are hashed using SHA-256 before storage.
- **Session Management**: Users stay logged in during the session using Streamlit's session_state.
- **API Key Masking**: API keys are masked in UI (first 4 and last 4 characters visible).
- **Role-Based Access**: Admin and user roles with appropriate permissions.
- **No Hardcoded Credentials**: All credentials are stored securely in JSON files with proper hashing.

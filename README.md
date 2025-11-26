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

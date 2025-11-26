⚡ GenAI-Powered STA Debugger
=============================

AI-powered analysis for semiconductor timing closure

Overview
--------
The **STA Debugger** is a web-based AI tool that automates the analysis of Static Timing Analysis (STA) reports, identifies timing violations, and provides expert-level recommendations to help engineers achieve faster timing closure.

It simplifies one of the most time-consuming stages in chip design — debugging STA reports — by combining the analytical accuracy of open-source EDA tools like **OpenSTA** with the intelligence of **Generative AI (Groq API)**.

The platform features a **Streamlit-based interface** for ease of use and generates detailed reports in both **JSON** and **PDF** formats.

Team
----
- **Tushar Bhandari** — Machine Learning & Backend Development  
- **Atharva Awate** — Frontend and System Integration  
- **Yash Pahade** — Data Analysis & Report Generation  

Features
--------
- **AI-Powered Analysis:**  
  Provides in-depth reasoning, root causes, severity level, and design-level fixes for each timing violation using **Groq’s LLM** (``llama-3.3-70b-versatile``).

- **Interactive Web Interface:**  
  A clean and intuitive **Streamlit** interface for uploading reports, configuring analysis options, and reviewing AI-generated results.

- **Report Generation:**  
  Download complete analysis results in **JSON** and **PDF** formats for documentation and sharing.

- **Support for Standard STA Formats:**  
  Compatible with STA reports from **Synopsys PrimeTime** and **OpenSTA**.

- **Fast and Insightful:**  
  Reduces debugging time from hours to minutes with detailed AI reasoning and actionable insights.

How It Works
------------
1. **Upload Report** — Upload an STA timing report (``.txt``, ``.rpt``, or ``.log``).  
2. **Parse Report** — A custom ``STAParser`` extracts key timing information (start points, endpoints, logic chains, slack).  
3. **AI Analysis** — Parsed data is processed by **Groq’s LLM** for quantitative reasoning and optimization suggestions.  
4. **Review Results** — Insights are displayed in a Streamlit dashboard with expandable path-level views.  
5. **Export Reports** — Download detailed results in **JSON** or **PDF** formats.

Usage Instructions
------------------
1. **Get an API Key:**  
   Sign up at `Groq Console <https://console.groq.com/>`_ for free access.

2. **Upload Report:**  
   Upload your STA timing report (``.txt``, ``.rpt``, ``.log``).

3. **Configure Options:**  
   Choose analysis options in the sidebar.

4. **Analyze:**  
   Click **Run Analysis** to start AI-powered debugging.

5. **Review Results:**  
   Examine detailed AI insights and recommendations.

6. **Export:**  
   Download comprehensive reports in **JSON** or **PDF** formats.

Installation and Setup
----------------------
**Prerequisites**
- Python 3.8+  
- Groq API Key  
- Internet connection for Streamlit and API inference

**Installation**
::

    git clone https://github.com/Atharva12210985/AI-Powered-Static-Timing-Violation-Debugger-.git
    cd AI-Powered-Static-Timing-Violation-Debugger-
    pip install -r requirements.txt

**Set your Groq API Key:**
Create a ``.env`` file:
::

    GROQ_API_KEY="your_api_key_here"

Run the Application
-------------------
Launch the Streamlit UI:
::

    streamlit run app/ui.py

Once running, open your browser to the Streamlit local URL displayed in the terminal.

Alternatively, access the hosted version directly:  
🌐 **Live Demo:** https://sta-debug-app.streamlit.app

System Architecture
-------------------
A visual representation of the complete system workflow has been provided as an image in the **GitHub project folder**.  
It illustrates the process from **OpenSTA Report Generation → AI-based Analysis → Streamlit Visualization and Reporting**.

Codebase Overview
-----------------
- **app/ui.py:** Streamlit interface handling user inputs and displaying results.  
- **app/utils.py:** Report parsing (``STAParser``) and PDF report generation.  
- **app/inference.py:** AI model logic and analysis using Groq API.  
- **app/models.py:** Pydantic data models for structured path and result representation.  
- **app/constants.py:** Prompt templates defining the AI reasoning structure and examples.

Demo Video
----------
We have uploaded a **demo video** in the GitHub project folder demonstrating the full functionality of the tool.

The video showcases:
- Uploading STA reports  
- Running AI-based analysis  
- Viewing violation causes and recommendations  
- Exporting results as JSON/PDF  

Example Workflow Summary
------------------------
+------+-------------------------+-------------------------+--------------------+
| Step | Input                   | Process                 | Output             |
+======+=========================+=========================+====================+
| 1    | STA Report (``.txt``)   | Parsed by ``STAParser`` | Structured data    |
+------+-------------------------+-------------------------+--------------------+
| 2    | Parsed paths            | Sent to Groq API        | AI insights        |
+------+-------------------------+-------------------------+--------------------+
| 3    | AI response             | Rendered on UI          | Interactive output |
+------+-------------------------+-------------------------+--------------------+
| 4    | User export             | JSON/PDF generator      | Downloadable file  |
+------+-------------------------+-------------------------+--------------------+

Future Enhancements
-------------------
- Integration with **OpenLane** for complete P&R + STA flow  
- **Multi-corner, Multi-mode (MCMM)** STA support  
- Domain-specific fine-tuned AI model for timing data  
- Cloud-hosted platform with user authentication and saved analysis history  

Submitting
----------
This project was developed as part of the **Microwatt Challenge Hackathon**.  
The final submission includes:

- Complete source code for backend, frontend, and AI logic  
- Updated documentation (``README.md`` and ``README.rst``)  
- Hosted live web app for demonstration  
- Example STA reports and output files in the ``/samples/`` folder  
- Uploaded demo video in the GitHub project folder  

For evaluation, please visit:  
🌐 **Live Demo:** https://sta-debug-app.streamlit.app

**GitHub Repository:** https://github.com/Atharva12210985/AI-Powered-Static-Timing-Violation-Debugger-

License
-------
This project is licensed under the **MIT License**.  

See the ``LICENSE`` file for details.

---

*Accelerating semiconductor design with AI — making STA debugging faster, smarter, and more accessible.*

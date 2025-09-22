# STA Debugger

The STA Debugger is a web-based tool that uses AI to analyze Static Timing Analysis (STA) reports, identify timing violations, and provide expert-level recommendations for fixing them. The application is built with Streamlit for the user interface and leverages the Groq API for its AI analysis capabilities.

---

## ✨ Features

- **AI-Powered Analysis:** Provides detailed insights, root causes, severity, and actionable fixes for timing violations.
- **Interactive UI:** A user-friendly interface built with Streamlit for uploading reports, configuring analysis options, and reviewing results.
- **Report Generation:** Allows users to download detailed analysis reports in both JSON and PDF formats.
- **Support for Standard Formats:** The parser is designed to work with standard STA report formats from tools like Synopsys PrimeTime and OpenSTA.

---

## 🛠️ How it Works

The application follows a simple workflow:

1. **File Upload:** Upload an STA timing report (`.txt`, `.rpt`, or `.log`).
2. **Report Parsing:** A custom `STAParser` class extracts key timing information (start/end points, slack, logic chain) into a structured format.
3. **AI Inference:** Parsed data for violated paths is sent to the LLM (`llama-3.3-70b-versatile` from Groq) with a detailed prompt for quantitative analysis, root cause, severity, and specific fixes.
4. **Results Display:** Analysis results are shown in the web UI with expandable sections for each timing path.
5. **Download:** Download the complete analysis in JSON or a formatted PDF.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- A Groq API Key (get one free from the [Groq Console](https://console.groq.com/))

### Installation

Clone the repository:

```bash
git clone https://github.com/Tushar-2004/STA-debugger.git
cd STA-debugger
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Set your Groq API key:  
The `TimingAnalyzer` class reads the API key from the `GROQ_API_KEY` environment variable. You can set it directly or use a `.env` file:

```env
GROQ_API_KEY="your_api_key_here"
```

---

## Usage

Run the Streamlit application:

```bash
streamlit run app/ui.py
```

Open your browser to the local URL provided by Streamlit.

**Instructions:**
- Enter your Groq API key.
- Upload your STA timing report file (`.txt`, `.rpt`, or `.log`).
- (Optional) Configure analysis options (e.g., analyze only violations).
- Click "Run Analysis" for AI-powered insights.

---

## 📂 Codebase Overview

- **app/ui.py:** Main Streamlit web interface functions (`setup_sidebar()`, `display_analysis_results()`, `main_ui()`).
- **app/utils.py:** Utility classes/functions for parsing reports and generating PDFs (`STAParser`, `generate_pdf_report()`).
- **app/inference.py:** AI model and analysis process (`TimingAnalyzer` initializes Groq model and invokes chain with prompt template).
- **app/models.py:** Data structures for timing paths, analysis suggestions, and overall results (`TimingPath`, `AnalysisSuggestion`, `ViolationAnalysis`, `AnalysisReport` via Pydantic).
- **app/constants.py:** Stores the `PROMPT_TEMPLATE` defining AI’s role, tasks, analysis framework, output format, and few-shot examples.

---

## 🙋‍♂️ Contributing

Pull requests and issues are welcome! Please submit bug reports, suggestions, or improvements.


---

## Author

[Tushar-2004](https://github.com/Tushar-2004)

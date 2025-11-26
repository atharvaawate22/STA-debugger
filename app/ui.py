import streamlit as st
import pandas as pd
import json
import tempfile
from datetime import datetime
from typing import List, Dict, Any
from app.utils import STAParser, generate_pdf_bytes
from app.inference import TimingAnalyzer
from app.models import TimingPath
from api_manager import get_api_key
from logger import log_action


def setup_sidebar() -> Dict[str, Any]:
    """Setup sidebar configuration"""
    st.sidebar.header("⚙️ Configuration")

    # Get API key from stored configuration
    api_key = get_api_key()
    if not api_key:
        st.sidebar.error("❌ API key not configured. Please contact admin.")
    else:
        st.sidebar.success("✅ API key configured")

    st.sidebar.header("📁 Upload Files")
    timing_file = st.sidebar.file_uploader(
        "STA Timing Report",
        type=['txt', 'rpt', 'log'],
        help="Upload your Static Timing Analysis report"
    )

    st.sidebar.header("🔧 Analysis Options")
    analyze_violations_only = st.sidebar.checkbox(
        "Analyze violations only",
        value=True,
        help="Only analyze paths with timing violations"
    )

    show_raw_data = st.sidebar.checkbox(
        "Show raw parsed data",
        value=False
    )

    return {
        "api_key": api_key,
        "timing_file": timing_file,
        "analyze_violations_only": analyze_violations_only,
        "show_raw_data": show_raw_data
    }


def display_analysis_results(analyses: List[Dict], config: Dict):
    """Display analysis results in an interactive format"""
    st.header("🤖 AI Analysis Results")

    # Summary statistics
    total = len(analyses)
    violated = sum(1 for a in analyses if a.get('status') == 'VIOLATED')
    met = total - violated

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Paths", total)
    with col2:
        st.metric("Violations", violated, delta=f"-{violated}" if violated else None)
    with col3:
        st.metric("Met Timing", met)

    # Detailed analysis for each path
    for i, analysis in enumerate(analyses, 1):
        with st.expander(f"Path {i}: {analysis.get('startpoint')} → {analysis.get('endpoint')}"):
            col1, col2 = st.columns([1, 2])

            with col1:
                st.subheader("Path Details")
                st.info(f"**Type:** {analysis.get('path_type')}")
                status = analysis.get('status')
                if status == "VIOLATED":
                    st.error(f"**Status:** {status} (Slack: {analysis.get('slack')} ns)")
                    st.error(f"**Severity:** {analysis.get('severity', 'unknown')}")
                else:
                    st.success(f"**Status:** {status}")

                st.write(f"**Startpoint:** {analysis.get('startpoint')}")
                st.write(f"**Endpoint:** {analysis.get('endpoint')}")

            with col2:
                st.subheader("Technical Analysis")
                if status == "VIOLATED":
                    st.write(f"**Root Cause:** {analysis.get('root_cause')}")
                    st.write(f"**Estimated Effort:** {analysis.get('estimated_effort')}")

                    st.subheader("Recommended Fixes")
                    suggestions = analysis.get('suggestions', [])
                    for j, suggestion in enumerate(suggestions, 1):
                        priority = suggestion.get('priority', '').upper()
                        priority_color = {
                            'HIGH': 'red',
                            'MEDIUM': 'orange',
                            'LOW': 'green'
                        }.get(priority, 'gray')

                        st.markdown(
                            f"**{j}. {suggestion.get('fix')}** "
                            f"<span style='color:{priority_color}'>[{priority}]</span>",
                            unsafe_allow_html=True
                        )
                        st.caption(f"*{suggestion.get('explanation')}*")
                else:
                    st.success("✅ Timing requirements met successfully")


def create_download_buttons(analyses: List[Dict], parsed_paths: List[TimingPath]):
    """Create download buttons for analysis results"""
    username = st.session_state.get("username", "Unknown")
    
    col1, col2 = st.columns(2)

    with col1:
        # JSON download
        json_data = json.dumps({
            "timestamp": datetime.now().isoformat(),
            "analyses": analyses,
            "original_paths": [p.dict() for p in parsed_paths]
        }, indent=2)

        if st.download_button(
            label="📥 Download JSON Report",
            data=json_data,
            file_name="timing_analysis.json",
            mime="application/json"
        ):
            log_action(username, "Download JSON Report", {
                "total_paths": len(analyses)
            })

    with col2:
        # Generate PDF bytes and create download button
        try:
            pdf_bytes = generate_pdf_bytes(analyses)
            if st.download_button(
                label="📄 Download PDF Report",
                data=pdf_bytes,
                file_name="timing_analysis_report.pdf",
                mime="application/pdf",
                key="pdf_download"
            ):
                log_action(username, "Download PDF Report", {
                    "total_paths": len(analyses)
                })
        except Exception as e:
            st.error(f"PDF generation failed: {str(e)}")

def show_instructions():
    """Show usage instructions"""
    st.info("""
    ## 📋 How to Use This Tool

    1. **Get API Key**: Sign up at [Groq Console](https://console.groq.com/) for free access
    2. **Upload Report**: Upload your STA timing report (.txt, .rpt, .log)
    3. **Configure**: Choose analysis options in the sidebar
    4. **Analyze**: Click the 'Run Analysis' button
    5. **Review**: Examine AI-powered insights and recommendations
    6. **Export**: Download detailed reports in JSON or PDF format

    ## 🎯 Supported Formats

    The parser works with standard STA report formats from tools like:
      - OpenSTA
    """)


def main_ui():
    """Main UI function"""
    config = setup_sidebar()
    
    # Get current username from session state
    username = st.session_state.get("username", "Unknown")

    if config["timing_file"] and config["api_key"]:
        if st.button("🚀 Run Analysis", type="primary"):
            # Log the action
            log_action(username, "Run STA Analysis", {
                "filename": config["timing_file"].name,
                "analyze_violations_only": config["analyze_violations_only"]
            })
            
            with st.spinner("Parsing timing report..."):
                report_content = config["timing_file"].getvalue().decode("utf-8")
                parser = STAParser(report_content)
                parsed_paths = parser.parse()

            if not parsed_paths:
                st.warning("No valid timing paths found in the report")
                log_action(username, "STA Analysis Failed", {"reason": "No valid timing paths found"})
                return

            # Filter paths if needed
            if config["analyze_violations_only"]:
                paths_to_analyze = [p for p in parsed_paths if p.status == "VIOLATED"]
                st.info(f"Analyzing {len(paths_to_analyze)} violated paths (of {len(parsed_paths)} total)")
            else:
                paths_to_analyze = parsed_paths

            # Show raw data if requested
            if config["show_raw_data"]:
                with st.expander("📊 Raw Parsed Data"):
                    st.json([p.dict() for p in parsed_paths])

            # Run analysis
            with st.spinner("Running AI analysis..."):
                analyzer = TimingAnalyzer(config["api_key"])
                analyses = analyzer.analyze_paths(paths_to_analyze)
                
                # Log analysis completion
                log_action(username, "STA Analysis Completed", {
                    "total_paths": len(analyses),
                    "violated_paths": sum(1 for a in analyses if a.get('status') == 'VIOLATED')
                })

            # Display results
            display_analysis_results(analyses, config)
            create_download_buttons(analyses, parsed_paths)

    elif not config["api_key"]:
        st.error("❌ API key is not configured. Please contact your administrator to set up the API key.")
        show_instructions()
    else:
        show_instructions()
"""Streamlit web interface for DataBuddy.

This is a thin UI layer around the existing DataBuddy backend.
All question handling, routing, conversation memory, analysis generation,
and LLM calls go through the existing DataBuddy pipeline.
"""

from html import escape
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Page configuration (must be the first Streamlit command)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DataBuddy — AI Data Analyst",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Ensure the project root is importable (handles `streamlit run` from any cwd)
# ---------------------------------------------------------------------------
import sys

_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.legacy.streamlit_support import load_streamlit_secrets  # noqa: E402
load_streamlit_secrets(st.secrets)

from backend.core import config  # noqa: E402
from backend.core.databuddy import AskResult  # noqa: E402
from backend.core.dataset_state import SUPPORTED_EXTENSIONS  # noqa: E402
from backend.core.llm_clients import ProviderError  # noqa: E402
from backend.legacy.ui_state import (  # noqa: E402
    initialize_session, replace_dataset, reset_conversation, clear_dataset,
    upload_fingerprint, append_message,
)

# ---------------------------------------------------------------------------
# Plotly import (for rendering chart JSON)
# ---------------------------------------------------------------------------
try:
    import plotly.io as pio
    _PLOTLY_AVAILABLE = True
except ImportError:
    _PLOTLY_AVAILABLE = False

# ---------------------------------------------------------------------------
# Supported upload extensions
# ---------------------------------------------------------------------------
_SUPPORTED_EXTENSIONS = [ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS]

# ---------------------------------------------------------------------------
# Premium CSS injection
# ---------------------------------------------------------------------------
_CUSTOM_CSS = """
<style>
/* ---------- Google Font ---------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ---------- Global ---------- */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ---------- Hide default Streamlit branding ---------- */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* ---------- Main container breathing room ---------- */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 56rem;
}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #12141D 0%, #1A1D29 100%);
    border-right: 1px solid rgba(108, 99, 255, 0.15);
}

section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #FAFAFA;
}

/* ---------- Hero / Header area ---------- */
.hero-container {
    text-align: center;
    padding: 2rem 1rem 1.5rem 1rem;
    margin-bottom: 1rem;
}
.hero-title {
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, #6C63FF 0%, #A78BFA 50%, #F472B6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.3rem;
    letter-spacing: -0.5px;
}
.hero-subtitle {
    font-size: 1.05rem;
    color: #9CA3AF;
    font-weight: 400;
    letter-spacing: 0.3px;
}

/* ---------- Welcome card (before dataset uploaded) ---------- */
.welcome-card {
    background: linear-gradient(135deg, rgba(108, 99, 255, 0.08) 0%, rgba(167, 139, 250, 0.06) 100%);
    border: 1px solid rgba(108, 99, 255, 0.2);
    border-radius: 16px;
    padding: 2.5rem 2rem;
    text-align: center;
    margin: 2rem auto;
    max-width: 32rem;
}
.welcome-icon {
    font-size: 3.5rem;
    margin-bottom: 0.8rem;
}
.welcome-heading {
    font-size: 1.3rem;
    font-weight: 600;
    color: #E5E7EB;
    margin-bottom: 0.5rem;
}
.welcome-text {
    font-size: 0.92rem;
    color: #9CA3AF;
    line-height: 1.6;
}

/* ---------- Dataset info card in sidebar ---------- */
.dataset-card {
    background: rgba(108, 99, 255, 0.06);
    border: 1px solid rgba(108, 99, 255, 0.15);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
}
.dataset-filename {
    font-size: 0.85rem;
    font-weight: 600;
    color: #A78BFA;
    margin-bottom: 0.5rem;
    word-break: break-all;
}
.dataset-stat {
    display: inline-block;
    background: rgba(108, 99, 255, 0.12);
    border-radius: 8px;
    padding: 0.35rem 0.8rem;
    margin: 0.15rem 0.3rem 0.15rem 0;
    font-size: 0.8rem;
    color: #D1D5DB;
}
.dataset-stat strong {
    color: #FAFAFA;
}

/* ---------- Chat messages ---------- */
[data-testid="stChatMessage"] {
    border-radius: 12px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    border: 1px solid rgba(255, 255, 255, 0.04);
    animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ---------- Chat input ---------- */
[data-testid="stChatInput"] textarea {
    border-radius: 12px !important;
    border: 1px solid rgba(108, 99, 255, 0.3) !important;
    transition: border-color 0.2s ease;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #6C63FF !important;
    box-shadow: 0 0 0 2px rgba(108, 99, 255, 0.15) !important;
}

/* ---------- Buttons ---------- */
.stButton > button {
    border-radius: 10px;
    font-weight: 500;
    transition: all 0.2s ease;
    border: 1px solid rgba(108, 99, 255, 0.3);
}
.stButton > button:hover {
    border-color: #6C63FF;
    box-shadow: 0 0 16px rgba(108, 99, 255, 0.2);
    transform: translateY(-1px);
}

/* ---------- File uploader ---------- */
[data-testid="stFileUploader"] {
    border-radius: 12px;
}
[data-testid="stFileUploader"] section {
    border-radius: 12px;
    border: 2px dashed rgba(108, 99, 255, 0.3);
    transition: border-color 0.2s ease;
}
[data-testid="stFileUploader"] section:hover {
    border-color: rgba(108, 99, 255, 0.6);
}

/* ---------- Expander ---------- */
.streamlit-expanderHeader {
    font-weight: 500;
    border-radius: 8px;
}

/* ---------- Metric cards ---------- */
[data-testid="stMetric"] {
    background: rgba(108, 99, 255, 0.06);
    border: 1px solid rgba(108, 99, 255, 0.12);
    border-radius: 10px;
    padding: 0.7rem 0.9rem;
}
[data-testid="stMetric"] label {
    color: #9CA3AF !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-weight: 700;
    color: #FAFAFA !important;
}

/* ---------- Scrollbar ---------- */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: rgba(108, 99, 255, 0.3);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(108, 99, 255, 0.5);
}

/* ---------- Divider ---------- */
hr {
    border-color: rgba(108, 99, 255, 0.12) !important;
}

/* ---------- Sidebar footer badge ---------- */
.sidebar-badge {
    text-align: center;
    padding: 0.6rem;
    margin-top: 1.5rem;
    font-size: 0.72rem;
    color: #6B7280;
    letter-spacing: 0.3px;
}
.sidebar-badge a {
    color: #A78BFA;
    text-decoration: none;
}

/* ---------- Chart container ---------- */
.chart-container {
    border: 1px solid rgba(108, 99, 255, 0.15);
    border-radius: 12px;
    padding: 0.5rem;
    margin: 0.5rem 0;
    background: rgba(108, 99, 255, 0.03);
}

/* ---------- Suggestion banner ---------- */
.viz-suggestion {
    background: linear-gradient(135deg, rgba(52, 211, 153, 0.08) 0%, rgba(96, 165, 250, 0.08) 100%);
    border: 1px solid rgba(52, 211, 153, 0.2);
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin-top: 0.5rem;
    font-size: 0.88rem;
    color: #D1D5DB;
}

/* ---------- Chart memory badge in sidebar ---------- */
.chart-memory-badge {
    background: rgba(244, 114, 182, 0.08);
    border: 1px solid rgba(244, 114, 182, 0.2);
    border-radius: 10px;
    padding: 0.6rem 1rem;
    margin: 0.5rem 0;
    font-size: 0.8rem;
    color: #D1D5DB;
}
.chart-memory-badge strong {
    color: #F472B6;
}
</style>
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_api_keys() -> list[str]:
    # Groq alone works through local routing. Mistral alone supports fallback.
    return [] if (config.GROQ_API_KEY or config.MISTRAL_API_KEY) else ["GROQ_API_KEY or MISTRAL_API_KEY"]


def _load_dataset(uploaded_file) -> None:
    if uploaded_file.size > config.MAX_UPLOAD_BYTES:
        raise ValueError("This file is larger than the 20 MB upload limit.")
    replace_dataset(st.session_state, uploaded_file.name, uploaded_file.getvalue())


def _render_chart(chart_json: str, msg_index: int) -> None:
    """Use browser PNG export; prepare HTML only when requested."""
    if not _PLOTLY_AVAILABLE:
        st.warning("Chart display is unavailable. Install the project requirements.")
        return
    try:
        fig = pio.from_json(chart_json)
        st.plotly_chart(
            fig, width="stretch", theme="streamlit", key=f"chart_{msg_index}",
            alt="Analysis chart. Use the computed evidence below for the plotted values.",
            config={"displaylogo": False, "toImageButtonOptions": {
                "format": "png", "filename": "databuddy_chart", "width": 1200,
                "height": 600, "scale": 2,
            }},
        )
        st.caption("Use the chart's camera button for PNG. Prepare HTML for an interactive download.")
        if st.button("Prepare HTML download", key=f"prepare_export_{msg_index}"):
            # CDN keeps the file small. No local browser or image renderer is needed.
            html = pio.to_html(fig, include_plotlyjs="cdn", full_html=True)
            st.download_button("Download interactive HTML", data=html,
                               file_name="databuddy_chart.html", mime="text/html",
                               key=f"export_{msg_index}", on_click="ignore")
            st.caption("The HTML download needs internet to load Plotly. It includes the plotted data.")
    except Exception:
        st.warning("This chart could not be displayed. Your computed answer is still available.")


def _render_suggestion(suggestion: str, msg_index: int) -> None:
    if suggestion:
        st.markdown(f'<div class="viz-suggestion">💡 {escape(suggestion)}</div>', unsafe_allow_html=True)


def _render_evidence(msg: dict, index: int) -> None:
    if msg.get("result_text") or msg.get("code"):
        with st.expander("Computed evidence and calculation"):
            if msg.get("result_text"):
                st.text(msg["result_text"])
            if msg.get("code"):
                st.code(msg["code"], language="python")


def main() -> None:
    initialize_session(st.session_state)
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-container"><div class="hero-title">DataBuddy</div>'
        '<div class="hero-subtitle">Your AI-powered conversational data analyst</div></div>',
        unsafe_allow_html=True,
    )
    missing_keys = _check_api_keys()
    if missing_keys:
        st.warning("Add a Groq or Mistral API key in local .env or Streamlit Secrets to enable analysis.", icon="🔑")
    with st.sidebar:
        st.markdown("### 📂 Dataset")
        st.caption("CSV or XLSX · maximum 20 MB. Demo data only.")
        uploaded_file = st.file_uploader(
            "Upload a dataset", type=_SUPPORTED_EXTENSIONS,
            max_upload_size=config.MAX_UPLOAD_MB,
            help="CSV is the main demo format. XLSX workbooks use the first sheet. No file or chat is saved for later sessions.",
            key=f"dataset_upload_{st.session_state.uploader_generation}",
            label_visibility="collapsed",
        )
        if uploaded_file is not None:
            fingerprint = upload_fingerprint(uploaded_file.name, uploaded_file.getbuffer())
            if fingerprint != st.session_state.dataset_fingerprint:
                if fingerprint != st.session_state.rejected_fingerprint:
                    try:
                        with st.spinner("Reading and checking your dataset…"):
                            _load_dataset(uploaded_file)
                        st.toast("Dataset loaded. The conversation is ready.")
                    except ValueError as error:
                        st.session_state.rejected_fingerprint = fingerprint
                        st.session_state.rejected_error = str(error)
                    except Exception:
                        st.session_state.rejected_fingerprint = fingerprint
                        st.session_state.rejected_error = "This file could not be loaded. Try a valid CSV or XLSX file."
                if fingerprint == st.session_state.rejected_fingerprint:
                    st.error(st.session_state.rejected_error)
                    if st.session_state.buddy is not None:
                        st.caption("Your previous dataset is still active.")
        info = st.session_state.dataset_info
        if info:
            st.markdown("---")
            st.markdown(
                '<div class="dataset-card">'
                f'<div class="dataset-filename">📄 {escape(st.session_state.dataset_name)}</div>'
                f'<span class="dataset-stat"><strong>{info["rows"]:,}</strong> rows</span>'
                f'<span class="dataset-stat"><strong>{info["cols"]}</strong> columns</span>'
                f'<span class="dataset-stat"><strong>{info["missing"]:,}</strong> missing</span></div>',
                unsafe_allow_html=True,
            )
            for warning in info.get("warnings", []):
                st.warning(warning)
            with st.expander("📋 Column details"):
                st.dataframe({"Column": info["columns"], "Type": [info["dtypes"][c] for c in info["columns"]]},
                             hide_index=True, width="stretch", alt="Detected dataset columns and types")
            with st.expander("👀 Preview (first 5 rows)"):
                st.dataframe(info["preview"], width="stretch", hide_index=True,
                             alt="First five rows of the active dataset")
        buddy = st.session_state.buddy
        if buddy is not None:
            if buddy.conversation.has_chart_context:
                st.caption(f"{len(buddy.conversation.chart_history)} recent chart(s) available for follow-up changes.")
            st.markdown("---")
            if st.button("🔄 Reset conversation", width="stretch"):
                reset_conversation(st.session_state)
                st.toast("Conversation and chart context cleared. Dataset kept.")
            if st.button("Remove dataset and clear session", width="stretch"):
                clear_dataset(st.session_state)
                st.rerun()
        st.caption("Session only. Refreshing or disconnecting may clear your data; closing the tab does not guarantee immediate server memory release.")
        st.caption("Samples, statistics, results and chat context may be sent to the configured model providers. Use non-sensitive demo data.")
        st.caption("Built with Streamlit · trusted personal demonstration")
    if st.session_state.buddy is None:
        st.markdown(
            '<div class="welcome-card"><div class="welcome-icon">📊</div>'
            '<div class="welcome-heading">Welcome to DataBuddy</div>'
            '<div class="welcome-text">Upload a CSV or XLSX file in the sidebar, then ask questions '
            'about its data or request an interactive chart.</div></div>', unsafe_allow_html=True,
        )
        return
    if len(st.session_state.messages) >= config.MAX_UI_MESSAGES:
        st.caption("Showing the most recent messages to keep this demo lightweight.")
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            if msg.get("chart_json"):
                _render_chart(msg["chart_json"], msg.get("id", str(i)))
            st.markdown(msg["content"])
            if msg.get("memory_notice"):
                st.caption(msg["memory_notice"])
            if msg.get("suggestion"):
                _render_suggestion(msg["suggestion"], i)
            _render_evidence(msg, i)
    question = st.chat_input("Ask anything about your data…", disabled=bool(missing_keys),
                             max_chars=config.MAX_QUESTION_CHARS)
    if question:
        append_message(st.session_state, {"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your question…"):
                try:
                    result = st.session_state.buddy.ask(question)
                except ProviderError as error:
                    result = AskResult(answer=str(error), status="error")
                except Exception:
                    result = AskResult(answer="This request could not be completed. Your dataset is still loaded; try a simpler question.", status="error")
            msg = {"role": "assistant", "content": result.answer,
                   "chart_json": result.chart_json, "suggestion": result.visualization_suggestion,
                   "result_text": result.result_text, "code": result.code,
                   "memory_notice": result.memory_notice}
            append_message(st.session_state, msg)
            if result.chart_json:
                _render_chart(result.chart_json, msg["id"])
            st.markdown(result.answer)
            if result.memory_notice:
                st.caption(result.memory_notice)
            if result.visualization_suggestion:
                _render_suggestion(result.visualization_suggestion, len(st.session_state.messages))
            _render_evidence(msg, len(st.session_state.messages))


main()

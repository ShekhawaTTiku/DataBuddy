"""Streamlit web interface for DataBuddy.

This is a thin UI layer around the existing DataBuddy backend.
All question handling, routing, conversation memory, analysis generation,
and LLM calls go through the existing DataBuddy pipeline.
"""

import os
import tempfile
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

_project_root = str(Path(__file__).resolve().parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from databuddy import DataBuddy  # noqa: E402

# ---------------------------------------------------------------------------
# Supported upload extensions
# ---------------------------------------------------------------------------
_SUPPORTED_EXTENSIONS = ["csv", "xlsx", "xls", "xlsm", "xlsb"]

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
</style>
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_api_keys() -> list[str]:
    """Return a list of missing API key names (empty list means all present)."""
    import config  # noqa: delayed import so dotenv is loaded first
    missing = []
    if not config.GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not config.MISTRAL_API_KEY:
        missing.append("MISTRAL_API_KEY")
    return missing


def _save_uploaded_file(uploaded_file) -> str:
    """Write the Streamlit UploadedFile to a temporary server-side path.

    Returns the path string suitable for DataBuddy(path).
    """
    suffix = Path(uploaded_file.name).suffix
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="databuddy_")
    try:
        os.write(fd, uploaded_file.getbuffer())
    finally:
        os.close(fd)
    return tmp_path


def _cleanup_temp_file(path: str | None) -> None:
    """Remove a temporary file if it exists."""
    if path is None:
        return
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
    except OSError:
        pass


def _init_session_state() -> None:
    """Initialise session-state keys if they don't already exist."""
    defaults = {
        "buddy": None,             # DataBuddy instance
        "dataset_name": None,      # filename of current dataset
        "dataset_info": None,      # dict with rows, cols, preview text
        "messages": [],            # UI chat history [{role, content}]
        "temp_path": None,         # path to temporary uploaded file
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _load_dataset(uploaded_file) -> None:
    """Create a new DataBuddy instance for the uploaded file.

    Handles temp-file lifecycle and session-state updates.
    """
    # Clean up previous temp file
    _cleanup_temp_file(st.session_state.temp_path)

    tmp_path = _save_uploaded_file(uploaded_file)
    st.session_state.temp_path = tmp_path

    buddy = DataBuddy(tmp_path)
    profile = buddy.dataset

    st.session_state.buddy = buddy
    st.session_state.dataset_name = uploaded_file.name
    st.session_state.dataset_info = {
        "rows": len(profile.df),
        "cols": len(profile.df.columns),
        "columns": [str(c) for c in profile.df.columns],
        "dtypes": {str(c): str(profile.df[c].dtype) for c in profile.df.columns},
        "missing": int(profile.df.isna().sum().sum()),
        "preview": profile.df.head(5),
    }
    # Clear UI chat when dataset changes
    st.session_state.messages = []


# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------

def main() -> None:
    _init_session_state()

    # Inject custom CSS
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

    # --- Gradient Header ---
    st.markdown(
        '<div class="hero-container">'
        '  <div class="hero-title">DataBuddy</div>'
        '  <div class="hero-subtitle">Your AI-powered conversational data analyst</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # --- API key check ---
    missing_keys = _check_api_keys()
    if missing_keys:
        st.warning(
            f"Missing API key(s): **{', '.join(missing_keys)}**. "
            "Set them in **Settings → Secrets** (Streamlit Cloud) or your `.env` file.",
            icon="🔑",
        )

    # --- Sidebar: upload & controls ---
    with st.sidebar:
        st.markdown("### 📂 Dataset")
        uploaded_file = st.file_uploader(
            "Upload a dataset",
            type=_SUPPORTED_EXTENSIONS,
            help="Supported: CSV, XLSX, XLS, XLSM, XLSB (up to 50 MB)",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            # Detect dataset change (new file or different file name/size)
            needs_load = (
                st.session_state.buddy is None
                or st.session_state.dataset_name != uploaded_file.name
            )

            if needs_load:
                try:
                    with st.spinner("Analyzing your dataset…"):
                        _load_dataset(uploaded_file)
                    st.toast(f"✅ Loaded **{uploaded_file.name}**", icon="📊")
                except (FileNotFoundError, ValueError) as e:
                    st.error(f"Could not load file: {e}", icon="❌")
                except Exception as e:
                    st.error(
                        f"Unexpected error: {type(e).__name__}: {e}",
                        icon="❌",
                    )

        # --- Dataset info card ---
        if st.session_state.dataset_info:
            info = st.session_state.dataset_info
            st.markdown("---")

            # File name and quick stats as HTML card
            stats_html = (
                '<div class="dataset-card">'
                f'  <div class="dataset-filename">📄 {st.session_state.dataset_name}</div>'
                f'  <span class="dataset-stat"><strong>{info["rows"]:,}</strong> rows</span>'
                f'  <span class="dataset-stat"><strong>{info["cols"]}</strong> columns</span>'
                f'  <span class="dataset-stat"><strong>{info["missing"]:,}</strong> missing</span>'
                '</div>'
            )
            st.markdown(stats_html, unsafe_allow_html=True)

            with st.expander("📋 Column details"):
                for col_name in info["columns"]:
                    dtype = info["dtypes"].get(col_name, "")
                    st.markdown(
                        f"<span style='color:#FAFAFA;font-size:0.85rem;'>`{col_name}`</span>"
                        f" <span style='color:#6B7280;font-size:0.75rem;'>({dtype})</span>",
                        unsafe_allow_html=True,
                    )

            with st.expander("👀 Preview (first 5 rows)"):
                st.dataframe(
                    info["preview"],
                    use_container_width=True,
                    hide_index=True,
                )

        # --- Reset & About ---
        if st.session_state.buddy is not None:
            st.markdown("---")
            if st.button("🔄 Reset conversation", use_container_width=True):
                st.session_state.buddy.conversation.clear()
                st.session_state.messages = []
                st.toast("Conversation reset!", icon="🔄")

        # Sidebar footer
        st.markdown(
            '<div class="sidebar-badge">'
            'Built with ❤️ using Streamlit'
            '</div>',
            unsafe_allow_html=True,
        )

    # --- Main area: Chat interface ---
    if st.session_state.buddy is None:
        # Welcome card
        st.markdown(
            '<div class="welcome-card">'
            '  <div class="welcome-icon">📊</div>'
            '  <div class="welcome-heading">Welcome to DataBuddy</div>'
            '  <div class="welcome-text">'
            '    Upload a CSV or Excel file in the sidebar to get started.<br>'
            '    Then ask questions about your data in plain English — '
            '    DataBuddy will analyze it for you.'
            '  </div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Suggestion chips
        st.markdown("")
        cols = st.columns(3)
        suggestions = [
            ("📈", "Trend analysis"),
            ("🔍", "Find outliers"),
            ("📊", "Summary stats"),
        ]
        for col, (icon, text) in zip(cols, suggestions):
            col.markdown(
                f"<div style='text-align:center;padding:0.8rem;background:rgba(108,99,255,0.06);"
                f"border:1px solid rgba(108,99,255,0.12);border-radius:10px;'>"
                f"<span style='font-size:1.5rem;'>{icon}</span><br>"
                f"<span style='font-size:0.8rem;color:#9CA3AF;'>{text}</span></div>",
                unsafe_allow_html=True,
            )
        return

    # Render existing chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if question := st.chat_input("Ask anything about your data…"):
        # Display user message
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Get answer from existing backend
        with st.chat_message("assistant"):
            with st.spinner("Analyzing…"):
                try:
                    answer = st.session_state.buddy.ask(question)
                except Exception as e:
                    answer = f"⚠️ An error occurred: {type(e).__name__}: {e}"
            st.markdown(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})


main()

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
    page_title="DataBuddy",
    page_icon="📊",
    layout="centered",
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
        "preview": profile.df.head(5),
    }
    # Clear UI chat when dataset changes
    st.session_state.messages = []


# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------

def main() -> None:
    _init_session_state()

    # --- Header ---
    st.title("📊 DataBuddy")
    st.caption("AI-powered conversational data analysis")

    # --- API key check ---
    missing_keys = _check_api_keys()
    if missing_keys:
        st.warning(
            f"Missing API key(s): **{', '.join(missing_keys)}**. "
            "Some features may not work. Set them in your `.env` file and restart.",
            icon="🔑",
        )

    # --- Sidebar: upload & controls ---
    with st.sidebar:
        st.header("Dataset")
        uploaded_file = st.file_uploader(
            "Upload a dataset",
            type=_SUPPORTED_EXTENSIONS,
            help="Supported formats: CSV, XLSX, XLS, XLSM, XLSB",
        )

        if uploaded_file is not None:
            # Detect dataset change (new file or different file name/size)
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            current_id = None
            if st.session_state.dataset_name and st.session_state.buddy:
                current_id = f"{st.session_state.dataset_name}_{st.session_state.temp_path}"

            needs_load = (
                st.session_state.buddy is None
                or st.session_state.dataset_name != uploaded_file.name
                or current_id is None
            )

            if needs_load:
                try:
                    with st.spinner("Loading dataset..."):
                        _load_dataset(uploaded_file)
                    st.success(f"Loaded **{uploaded_file.name}**", icon="✅")
                except (FileNotFoundError, ValueError) as e:
                    st.error(f"Could not load file: {e}", icon="❌")
                except Exception as e:
                    st.error(
                        f"Unexpected error loading dataset: {type(e).__name__}: {e}",
                        icon="❌",
                    )

        # --- Dataset info ---
        if st.session_state.dataset_info:
            info = st.session_state.dataset_info
            st.divider()
            st.subheader("Dataset Info")
            col1, col2 = st.columns(2)
            col1.metric("Rows", f"{info['rows']:,}")
            col2.metric("Columns", info["cols"])
            with st.expander("Column names"):
                for c in info["columns"]:
                    st.text(c)
            with st.expander("Preview (first 5 rows)"):
                st.dataframe(info["preview"], use_container_width=True)

        # --- Reset button ---
        if st.session_state.buddy is not None:
            st.divider()
            if st.button("🔄 Reset conversation", use_container_width=True):
                st.session_state.buddy.conversation.clear()
                st.session_state.messages = []
                st.success("Conversation reset.", icon="🔄")

    # --- Main area: Chat interface ---
    if st.session_state.buddy is None:
        st.info("👈 Upload a dataset to get started.", icon="📁")
        return

    # Render existing chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if question := st.chat_input("Ask DataBuddy a question..."):
        # Display user message
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Get answer from existing backend
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    answer = st.session_state.buddy.ask(question)
                except Exception as e:
                    answer = f"⚠️ An error occurred: {type(e).__name__}: {e}"
            st.markdown(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()

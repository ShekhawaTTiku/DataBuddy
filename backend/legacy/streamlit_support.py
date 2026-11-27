"""Streamlit-specific credential bootstrap, separate from the analysis core."""
import os

_SECRET_KEYS = (
    "GROQ_API_KEY", "GEMINI_API_KEY", "MEMORY_MODEL", "ROUTER_MODEL", "CHAT_MODEL",
    "GEMINI_EXPLANATION_MODEL", "GEMINI_FALLBACK_MODEL", "GEMINI_RESERVE_MODEL", "ANALYSIS_MODEL", "DATABUDDY_TIMEZONE",
)


def load_streamlit_secrets(secrets) -> None:
    """Only export known scalar settings; do not copy unrelated app secrets."""
    try:
        for key in _SECRET_KEYS:
            value = secrets.get(key)
            if isinstance(value, (str, int, float, bool)):
                os.environ.setdefault(key, str(value))
    except FileNotFoundError:
        return

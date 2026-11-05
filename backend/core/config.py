"""Environment-backed settings shared by CLI and UI; no Streamlit imports."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        raise ValueError(f"{name} must be a whole number.") from None
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return value


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MEMORY_MODEL = os.getenv("MEMORY_MODEL", "gemini-3.5-flash-lite")
ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "openai/gpt-oss-120b")
CONVERSATION_MODEL = os.getenv("MISTRAL_CHAT_MODEL", "ministral-8b-latest")
EXPLANATION_MODEL = os.getenv("MISTRAL_EXPLANATION_MODEL", "ministral-14b-latest")
FALLBACK_MODEL = os.getenv("MISTRAL_FALLBACK_MODEL", "ministral-14b-latest")
TIMEZONE = os.getenv("DATABUDDY_TIMEZONE", "Asia/Kolkata")
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes", "on")
ENABLE_VISUALIZATION_SUGGESTIONS = os.getenv("ENABLE_VISUALIZATION_SUGGESTIONS", "false").lower() in ("1", "true", "yes", "on")

# Upload limits are fixed for this small personal demonstration.
MAX_UPLOAD_MB = 20
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_DATASET_COLUMNS = 200
MAX_DATASET_ROWS = 250_000
MAX_PROFILE_CHARS = 12_000
MAX_QUESTION_CHARS = 4_000
MAX_MESSAGE_CHARS = 6_000
MAX_CONTEXT_CHARS = 12_000
MAX_PROMPT_CHARS = 28_000
MAX_CODE_CHARS = 16_000
MAX_CHART_BYTES = 1_000_000
MAX_WORKER_OUTPUT_BYTES = 1_500_000
MAX_UI_MESSAGES = 40
MEMORY_BATCH_SIZE = 6
MAX_MEMORY_NOTE_CHARS = 400
MAX_MEMORY_SUMMARY_CHARS = 2_000
MAX_MEMORY_RESPONSE_TOKENS = 768

MAX_CODE_RETRIES = _integer("MAX_CODE_RETRIES", 2, 0, 3)
EXEC_TIMEOUT_SECONDS = _integer("EXEC_TIMEOUT_SECONDS", 5, 1, 30)
SAMPLE_ROWS = _integer("SAMPLE_ROWS", 3, 0, 5)
MAX_RESULT_ROWS = _integer("MAX_RESULT_ROWS", 20, 1, 100)
MAX_RESULT_CHARS = _integer("MAX_RESULT_CHARS", 4_000, 200, 12_000)
MAX_RECENT_TURNS = _integer("MAX_RECENT_TURNS", 6, 1, 12)
MAX_RESPONSE_TOKENS = _integer("MAX_RESPONSE_TOKENS", 2_048, 256, 4_096)
PROVIDER_TIMEOUT_SECONDS = _integer("PROVIDER_TIMEOUT_SECONDS", 20, 1, 60)
REQUEST_TIMEOUT_SECONDS = _integer("REQUEST_TIMEOUT_SECONDS", 75, 5, 180)
PROVIDER_MAX_RETRIES = _integer("PROVIDER_MAX_RETRIES", 1, 0, 2)
MEMORY_TIMEOUT_SECONDS = _integer("MEMORY_TIMEOUT_SECONDS", 20, 1, 20)

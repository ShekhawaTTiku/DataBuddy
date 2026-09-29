import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Groq-hosted model placeholder (specify a current Groq model, e.g. "llama-3.3-70b-versatile")
ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "openai/gpt-oss-120b")
MEMORY_MODEL = os.getenv("MEMORY_MODEL", "gemini-3.6-flash")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
CONVERSATION_MODEL = os.getenv("MISTRAL_CHAT_MODEL", "ministral-8b-latest")
EXPLANATION_MODEL = os.getenv("MISTRAL_EXPLANATION_MODEL", "ministral-14b-latest")
FALLBACK_MODEL = os.getenv("MISTRAL_FALLBACK_MODEL", "mistral-medium-latest")
TIMEZONE = os.getenv("DATABUDDY_TIMEZONE", "Asia/Kolkata")
MODEL_NAME = ANALYSIS_MODEL  # backwards compatibility for the original client

MAX_CODE_RETRIES = int(os.getenv("MAX_CODE_RETRIES", "2"))
EXEC_TIMEOUT_SECONDS = int(os.getenv("EXEC_TIMEOUT_SECONDS", "5"))
SAMPLE_ROWS = int(os.getenv("SAMPLE_ROWS", "3"))
MAX_RESULT_ROWS = int(os.getenv("MAX_RESULT_ROWS", "20"))
MAX_RESULT_CHARS = int(os.getenv("MAX_RESULT_CHARS", "2000"))
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes", "on")
MAX_RECENT_TURNS = int(os.getenv("MAX_RECENT_TURNS", "6"))
SUMMARY_MAX_WORDS = int(os.getenv("SUMMARY_MAX_WORDS", "250"))

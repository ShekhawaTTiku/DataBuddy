# Setup and configuration

For the dedicated React/FastAPI app, use [working web app setup](WEBAPP_SETUP.md). The instructions below describe the retained legacy interfaces.

## Verified local environment

Windows and Python 3.11.9. Ten direct runtime dependencies are pinned in requirements/legacy.txt; requirements-lock-windows.txt records 63 installed runtime packages, including Google Gen AI for memory. It is an installed-environment snapshot, not a clean-install or cross-platform guarantee. Verify dependency resolution and tests on any different Python/OS before deployment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock-windows.txt
python -m pip install -r requirements/dev.txt
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
```

Edit .env privately and replace placeholders. For another OS, use requirements/legacy.txt and verify the resolved environment. No installation or package upgrade was performed during this work; existing installed packages were exercised.

## Provider settings

- GROQ_API_KEY: primary analysis/code generation and answer writing.
- GEMINI_API_KEY: request routing (`ROUTER_MODEL`, default `gemini-decision-1`), ordinary conversation (`CHAT_MODEL`, default `gemini-3.1-flash-lite`), saved-result explanations (`GEMINI_EXPLANATION_MODEL`, default `gemini-4-hydrogen`), Groq code/narration fallback (`GEMINI_FALLBACK_MODEL`, default `gemini-4-hydrogen`), and primary brief-note and rolling-summary engine (`MEMORY_MODEL`, default `gemini-3.5-flash-lite`). Without this key, local routing rules handle clear dataset requests and configured Mistral handles memory fallback.
- MISTRAL_API_KEY: retained for Gemini memory fallback only.
- Either key enables chat/data questions: without Gemini routing falls back to the local heuristic router; without Groq `GEMINI_FALLBACK_MODEL` handles analysis/narration when `GEMINI_API_KEY` is configured. Ordinary chat and saved-result explanations use `GEMINI_API_KEY`; prior evidence remains inspectable if explanation fails.
- ANALYSIS_MODEL, MEMORY_MODEL, ROUTER_MODEL, CHAT_MODEL, GEMINI_EXPLANATION_MODEL, GEMINI_FALLBACK_MODEL, MISTRAL_EXPLANATION_MODEL, MISTRAL_FALLBACK_MODEL select provider models. Role-appropriate defaults and official references are listed in [PROVIDERS_AND_MEMORY.md](PROVIDERS_AND_MEMORY.md); account access is not guaranteed. An unavailable model produces a configuration message rather than silent failover for chat/explanation/analysis (while routing falls back to local rules). Existing private .env files were not edited.
- Streamlit Cloud Secrets, if later used, are loaded only by streamlit_support.py. Core config never imports Streamlit. Only known scalar provider/model/time-zone settings are exported; unrelated secrets stay private.

## Useful optional settings

| Setting | Default | Allowed values/meaning |
| --- | --- | --- |
| MAX_CODE_RETRIES | 2 | 0–3 retries after rejected/failed generated code |
| EXEC_TIMEOUT_SECONDS | 5 | 1–30 seconds per worker |
| PROVIDER_TIMEOUT_SECONDS | 20 | 1–60 seconds per provider attempt |
| REQUEST_TIMEOUT_SECONDS | 75 | 5–180 seconds shared elapsed budget for model calls in a question |
| PROVIDER_MAX_RETRIES | 1 | 0–2 retries; SDK retry layers disabled |
| MAX_RESPONSE_TOKENS | 2048 | 256–4096 per model response |
| MAX_RECENT_TURNS | 6 | 1–12 recent question/answer pairs |
| MEMORY_TIMEOUT_SECONDS | 20 | 1–20 seconds for the optional memory update, within the question's overall deadline; below Gemini's 10-second minimum, Mistral is used if configured |
| SAMPLE_ROWS | 3 | 0–5 sample rows; setting zero does not remove statistics/category values |
| MAX_RESULT_ROWS | 20 | 1–100 displayed result rows |
| MAX_RESULT_CHARS | 4000 | 200–12000 result characters |
| ENABLE_VISUALIZATION_SUGGESTIONS | false | Optional extra model call after successful text analysis |
| DEBUG | false | Metadata-only diagnostic messages |
| DATABUDDY_TIMEZONE | Asia/Kolkata | IANA time zone for local clock answers |

Upload cap is fixed at 20 MiB; other fixed limits are documented in config.py. Memory responses are capped separately at 768 tokens; notes at 400 characters, the rolling paragraph at 2,000 characters and the batch at six notes. All model calls have bounded response tokens; even failed/retried calls may consume a provider's free quota. No paid upgrade or paid service is activated by this project. Timeout/retry bounds improve predictability but are not a billing guarantee; a provider may finish an already-started request after a disconnect.

## Run and verify

```powershell
python -m streamlit run web_app.py
python -m backend.cli examples/demo_sales.csv
python -m pytest -q
python -m pip check
```

The terminal supports /state, /reset and /quit. /reset clears session context; restarting the program starts fresh. Automated regression tests block external network connections and use fake provider clients/responses. Windows asyncio loopback socket pairs are permitted. No live model calls run in the test suite.

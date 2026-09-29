# DataBuddy

DataBuddy answers natural-language questions about local CSV and Excel files. Groq turns data questions into pandas code, the local executor runs that code against the in-memory DataFrame, and an LLM explains the computed result. The raw DataFrame is not sent to any LLM provider; the router receives only column names and conversation context.

## Setup

Use Python 3.10 or newer, install dependencies, and create a `.env` file with:

```text
GROQ_API_KEY=your-groq-key
GEMINI_API_KEY=your-gemini-key
MISTRAL_API_KEY=your-mistral-api-key
```

Groq handles primary data-analysis code and answers. Gemini is only used to summarize older conversation turns. Mistral provides Ministral 8B for routing and ordinary conversation, Ministral 14B for explaining the last successful analysis, and Mistral Medium as the analysis fallback when Groq is rate-limited or temporarily unavailable. Set `MISTRAL_CHAT_MODEL`, `MISTRAL_EXPLANATION_MODEL`, or `MISTRAL_FALLBACK_MODEL` to change those models. Mistral model aliases ending in `-latest` can change over time. Current clock answers use `DATABUDDY_TIMEZONE` (defaults to `Asia/Kolkata`).

```powershell
python -m pip install -r requirements.txt
python app.py uploads\sales.csv
```

Ask questions at the prompt. Data questions use the analysis pipeline; ordinary conversation uses the chat handler; current-time questions use the local clock; and “how did you know?” uses conversation context to explain the last analysis. Enter `/state` to inspect the current summary and recent turns, `/reset` to clear saved conversation state for this dataset, or `/quit` to exit. Conversation state is saved locally under `.databuddy_state/` and restored when you launch the same dataset again. Settings such as `DEBUG`, `SAMPLE_ROWS`, and `MAX_RECENT_TURNS` can be set as environment variables. Keep `.env` private; `.gitignore` excludes it, uploaded datasets, and saved conversation state.

The request router adds one Mistral classification request per message; ordinary conversation is answered in that same response. A request to explain an analysis uses a separate Ministral 14B call. Proactive Groq usage monitoring and in-session low-quota warnings are not implemented yet; analysis failover currently happens after Groq returns a rate-limit or temporary availability error.

## Architecture

- `app.py`: terminal interface.
- `databuddy.py`: orchestration and retry flow.
- `dataset_state.py` / `dataset_profiler.py`: local loading and compact dataset profile.
- `conversation_state.py`: recent turns and Gemini-backed summary folding.
- `analyst.py`: Groq prompts and response handling.
- `llm_clients.py`: provider SDK calls and bounded transient retries.
- `executor.py`: static code checks, restricted execution, timeout, and result truncation.
- `prompts/`: code generation, final answer, and summarization templates.

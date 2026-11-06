# Architecture

## Dedicated web application

Updated 2026-11-06 after the repository organization and chat release. `frontend/` contains the React/TypeScript interface. `backend/api/main.py` owns bounded in-memory sessions, streamed upload, idempotent background jobs, usage policy and explicit-origin bearer-token transport. `backend/core/telemetry.py` observes safe metadata/stages. `backend/core/response_stream.py` provides request-local text/evidence delivery and cancellation; `backend/api/streaming.py` holds the bounded current-job snapshot. Authenticated fetch/SSE delivers incremental answers and early evidence; `/api/job` remains recovery status and `/api/session` supplies canonical completed turns/usage. Stream attachment never creates work. Native dialogs provide data/calculation/chart inspection; Plotly loads on demand. Deployment uses one API worker because state is in-process. There is no database or migration layer. See [streaming](STREAMING.md).

## Retained interfaces

- `web_app.py`: compatibility launcher for `backend/legacy/web_app.py`, the retained Streamlit interface.
- `app.py`: compatibility launcher for `backend/cli.py`, which provides the terminal loop, session commands and computed evidence display.
- `backend/legacy/streamlit_support.py`: allowlisted Streamlit Secrets bootstrap, called before importing core config.
- `backend/legacy/ui_state.py`: content fingerprints, transactional dataset replacement, bounded display history and clear/reset helpers. No Streamlit imports or saved uploads.

## Reusable core

The following modules live in `backend/core/`; prompt templates live in `backend/core/prompts/`. Dependencies are grouped in `requirements/`, and production Docker copies only the API/core and their locked runtime dependencies.

- config.py: validated environment-backed settings; explicitly loads the project-local .env; no UI imports.
- dataset_profiler.py / dataset_state.py: bounded memory loading from paths, bytes and binary streams; CSV/XLSX parsing, conservative types/dates, clipped profile and import notices.
- databuddy.py: session coordinator. DataBuddy(dataset_source=None, filename=None).ask(question) returns AskResult with answer, optional chart/description/suggestion, result_text, code and status (success, partial, error, clarification, stopped). No-data sessions call the conversational model directly without generating code. Delivery callbacks expose evidence before narration and the answer before memory; the central recording path remains once per exchange.
- conversation_state.py: bounded in-memory recent turns, six brief notes, one rolling paragraph, last successful analysis and five recent charts. Optional Gemini/Mistral summarization; no file save/load. Summaries are excluded from code-generation analysis context, which retains actual recent analysis and saved computed evidence.
- message_handler.py: local clock handling, model routing with local fallback, conversation and prior-analysis explanation.
- analyst.py and prompts/: bounded prompt assembly, code generation and evidence-based narration. Optional suggestions default off.
- llm_clients.py: Groq/Gemini/Mistral SDK boundary, safe errors, per-attempt timeout, shared request budget, explicit token caps and role-specific transient fallback. Primary calls normally receive 60% of the remaining call budget when Mistral is configured. Gemini receives its required minimum 10-second deadline when enough time remains; otherwise it is skipped in favor of fallback. No SDK deadline exceeds the remaining overall budget.
- executor.py: validation, trusted-parent DataFrame serialization, disposable working directory, subprocess timeout, output cap and result validation.
- execution_policy.py: identical basic code rules used by parent and worker.
- _runner.py: no application config or credential loading; permitted module imports, bounded print capture, computation, chart validation and actual plotted evidence.

## Request flow

1. Conversation can start before an upload, using the existing Mistral model with current app facts, dataset availability, configured clock and bounded context. Every admitted message counts toward the allowance and memory cycle.
2. Upload is checked and parsed in memory. The active dataset switches only after success. First upload preserves introductory conversation; later replacement clears it. With a dataset loaded, existing local clock/remember handling remains available.
3. Router selects analysis, chart, chart modification, conversation or explanation; malformed/unavailable routing falls back to local rules.
4. Generated code is validated and executed in a fresh bounded worker, using a copy of the session DataFrame.
5. Successful evidence is preserved. Narration failure produces partial success; failed execution does not produce a fabricated narrative.
6. Record the exchange once and optionally create one memory note. On the sixth exchange, briefing and merging with the five notes/old paragraph share one provider request, producing one bounded replacement paragraph. Memory has a 20-second default sub-budget within the existing overall request deadline; failures retain recent context and expose a safe notice.
7. UI/CLI displays the answer, actual evidence and any memory limitation. UI charts use browser PNG export and opt-in HTML preparation.

See [provider roles and memory](PROVIDERS_AND_MEMORY.md) for model choices, rollover examples and failure behavior.

## Core/API boundary

The core imports no Streamlit code. The implemented API constructs a session coordinator and serializes AskResult, including bounded structured result tables. No accounts or database were added. Session ownership/authentication and hardened execution must be revisited if the audience expands beyond trusted demonstrations.

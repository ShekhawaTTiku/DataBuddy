# DataBuddy Project Guide

This document describes the current DataBuddy codebase as implemented. It explains what each component does, how a request travels through the system, why the main design choices were made, how to run the app, and what limitations should be understood before extending it or publishing a GitHub README.

> **Documentation scope:** `DataBuddy_Project.md` describes an earlier, simpler design. It is useful as project history, but it does not describe the current conversation handling, Mistral models, Gemini summaries, persisted state, or routing. This guide follows the code that currently exists.

## 1. What DataBuddy does

DataBuddy is a Python command-line chatbot for CSV and Excel datasets. It accepts ordinary language, chooses whether a message needs data analysis or conversation handling, and, for analysis, has an LLM produce pandas code that is executed locally against the loaded DataFrame. The computed output is then given to an LLM to explain.

The project also supports general chat, recalling recent conversation, answering local time/date questions, explaining its last successful analysis, and saving conversation state between runs.

The central idea behind data answers is to separate **understanding the request** from **calculating the answer**. An LLM writes code; local Python performs the calculation. This gives DataBuddy a real result to explain instead of asking a model to guess a number from a description of the data.

## 2. Request flow at a glance

```text
User types a message
        |
        v
app.py reads it and handles /state, /reset, and /quit
        |
        v
DataBuddy.ask()
        |
        +-- A direct "remember ..." statement without '?' --> acknowledge and save locally
        |
        +-- Recognized time/date question -------------------> answer from local clock
        |
        +-- Other message -----------------------------------> Ministral 8B classifies it
                                                               |
                  +--------------------------------------------+------------------+
                  |                                                               |
                  v                                                               v
          General conversation                                           Data-analysis request
          8B classification/reply                                       Groq writes pandas code
          in one API call                                                 |
                  |                                                       v
                  |                                              executor checks and runs code
                  |                                                       |
                  |                                         error? -- retry code generation
                  |                                                       |
                  |                                                       v
                  |                                              Groq explains result
                  |                                                       |
                  |                                             Groq outage/limit?
                  |                                                       |
                  |                                             Mistral Medium fallback
                  |
                  +-- Explain a previous analysis --> Ministral 14B with saved analysis evidence
        |
        v
Conversation and the latest successful analysis are saved locally
        |
        +-- When enough turns accumulate, Gemini summarizes older turns
```

The time and direct remember checks run before the LLM router. All other messages normally cause a router call. On a router API/JSON failure, a small local rule-based router is used. A normal conversational reply is returned in the router response itself; it does not normally require a second chat call.

## 3. Provider roles and API-call counts

| Provider/model setting | Job | Typical calls |
| --- | --- | --- |
| Mistral `ministral-8b-latest` (`MISTRAL_CHAT_MODEL`) | Route messages; answer ordinary conversation | One call for routing and ordinary chat together. One routing call before analysis or explanation. |
| Mistral `ministral-14b-latest` (`MISTRAL_EXPLANATION_MODEL`) | Explain the last successful analysis from stored evidence | One extra call after the router chooses explanation. |
| Groq `openai/gpt-oss-120b` (`ANALYSIS_MODEL`) | Generate analysis code and turn actual computed output into prose | Usually two calls for analysis, plus another code-generation call for each execution retry. |
| Mistral `mistral-medium-latest` (`MISTRAL_FALLBACK_MODEL`) | Replace an individual Groq analysis LLM call after Groq has exhausted transient retries | Called only after a retryable Groq outage/rate limit, not proactively. |
| Gemini `gemini-3.6-flash` (`MEMORY_MODEL`) | Fold older conversation turns into a compact summary | Called only when recent turns exceed `MAX_RECENT_TURNS`. |

The shared provider retry helper makes up to three attempts for recognized transient errors (initial call plus two retries), with short exponential delays. It does not retry all errors. A missing key, invalid model, or other non-transient API error is raised as a runtime error. Groq-to-Mistral failover is attached to each individual analysis-model call: code generation can fall back independently from final answer writing.

There is no current usage/quota polling or warning before an API limit is reached. Fallback starts only after a Groq call returns a recognized temporary failure or rate limit. If Mistral is itself rate-limited, fallback cannot complete either.

## 4. Data and privacy flow

The complete pandas DataFrame is loaded locally and is not uploaded as a file. The generated code is executed locally. However, prompts sent to providers can contain information derived from the dataset and conversation:

- **Groq code generation:** receives a profile with file name, row/column counts, column names/types, summary statistics, low-cardinality values, and up to `SAMPLE_ROWS` actual rows (three by default). Thus, some real cell values are sent; do not describe this as “no dataset data leaves the computer.”
- **Groq final answer:** receives the profile, generated code, compact actual result or execution error, and recent conversation context.
- **Mistral router/chat:** receives column names, the current message, and conversation context. The router prompt contains recent chat turns; personal facts in those turns can therefore be sent to Mistral.
- **Mistral explanation:** receives the latest analysis question, generated code, computed result, prior answer, and explanation request.
- **Gemini memory summary:** receives older turns selected to fold into the conversation summary.

Saved conversation JSON stays on disk in `.databuddy_state/`. It may include user-stated personal details, assistant replies, summaries, and the last analysis question/code/result/answer. Keep this directory and `.env` private. `/reset` removes the state file for the currently loaded dataset; `/quit` does not erase it.

## 5. Codebase map

### `app.py` — command-line entry point

Reads the dataset path from the command line, constructs `DataBuddy`, prints the loaded file dimensions, and runs the input loop. It handles `/state`, `/reset`, `/quit`, blank input, Ctrl+C/EOF, and displays exceptions from an individual request without closing the whole app.

**Why it is separate:** the terminal interface stays small; routing, analysis, and state are handled by their own modules.

### `databuddy.py` — request coordinator

`DataBuddy.__init__` loads and profiles the dataset once. It chooses the local conversation-state filename by hashing the lowercase resolved dataset path, then loads that state.

`DataBuddy.ask(question)` is the main request workflow:

1. Builds the conversation context.
2. Handles a non-question containing `remember` or `keep in mind` deterministically. It acknowledges that fact and saves it without making it a data filter.
3. Builds analysis-only context so chat details are not intentionally used as default dataset filters.
4. Calls the router and dispatches to clock, chat, explanation, or analysis.
5. For analysis, generates code, runs it, retries failed execution up to `MAX_CODE_RETRIES`, asks for a final explanation, and stores a successful analysis record.
6. Adds the turn to conversation state, which saves it to disk and may trigger summary folding.

The last successful analysis is preserved when a later attempt fails or returns `None`; it is replaced only by a successful non-`None` analysis result.

### `dataset_profiler.py` — loading and profiling

Defines `DatasetProfile` with the source filename, actual pandas DataFrame, and text profile. `load_and_profile(path)`:

- Checks that the path exists.
- Reads CSV as normal UTF-8 first and retries with Latin-1 if decoding fails.
- Reads Excel extensions `.xlsx`, `.xls`, `.xlsm`, and `.xlsb` through `pandas.read_excel` (some formats may need optional engines beyond the packages listed in requirements).
- Detects likely date columns by sampling string values and attempts conversion.
- Describes each column with a simplified dtype, unique/missing counts, numeric min/max/mean, date range, and values for low-cardinality text columns.
- Adds the first `SAMPLE_ROWS` rows to the profile.

**Why profile the dataset:** code generation needs column names and broad shape without sending a full table. The profile is compact relative to the DataFrame, though its size can grow with many columns or long sample values.

Date detection is heuristic. Mixed date formats can cause a pandas warning or conversion to `NaT`; a warning does not by itself mean the dataset failed to load.

### `dataset_state.py` — compatibility interface

Re-exports `DatasetProfile` and `load_and_profile`, and aliases `DatasetState` to `DatasetProfile`. This is a small public interface that keeps dataset loading details in `dataset_profiler.py`.

### `message_handler.py` — request routing and non-analysis answers

First checks a narrow set of time/date phrasings locally and returns the configured local time. Other messages are sent with the router template to Ministral 8B. The router response must be JSON with an allowed route and a reply field. If the call or JSON parsing fails, local regex and column-name heuristics choose a route.

General conversation uses the reply included by the router. If needed (for example, local routing fallback classified a message as conversation), it calls the conversation model with `conversation_response.txt`. Explanation requests use `analysis_explanation.txt` and the latest successful analysis. Clock replies use Python `datetime` and `zoneinfo`, controlled by `DATABUDDY_TIMEZONE`.

**Why have both LLM and local routing:** the LLM can understand varied phrasing; local rules allow deterministic handling for time and a best-effort route when the classifier fails. The heuristic fallback is intentionally simpler and can misclassify ambiguous phrasing.

### `analyst.py` — analysis prompts

`generate_code(...)` fills `code_generation.txt` with the profile, previous analysis context, any prior failed attempt, and the current question. It calls the shared analysis provider function and strips a surrounding Markdown code fence if present.

`write_answer(...)` fills `final_response.txt` with the question, profile, conversation context, code, execution status, and result/error. It then asks the analysis provider to describe the evidence in plain language.

**Why separate generation and explanation:** the code model proposes a computation, while the final-response model only sees what actually happened. This reduces the chance that the explanation invents a computed value.

### `executor.py` — bounded local code execution

The executor returns `ExecutionResult(ok, result_text, error)`.

1. Parses the generated code into a Python AST and rejects selected imports, calls, OS/network-related names, and dunder attributes.
2. Runs accepted code in a separate process with a copy of the DataFrame and only a restricted namespace containing `df`, `pd`, `np`, and a limited set of builtins.
3. Waits up to `EXEC_TIMEOUT_SECONDS`; terminates/kills the worker after timeout.
4. Reads the variable named `result`, converts it to text, truncates Series/DataFrames to `MAX_RESULT_ROWS`, and truncates text to `MAX_RESULT_CHARS`.
5. Returns execution exceptions in a short error string.

**Why use a child process:** a separate process can be stopped after a timeout, which an ordinary in-process timer cannot safely do for code stuck in a CPU loop.

**Security boundary:** these checks lower risk from accidentally unsafe generated code, but they are not a hardened security sandbox. AST deny-lists and Python namespace restrictions can have escape paths; the process still runs under the same operating-system account and permissions. Do not expose this executor to untrusted users or use it as the sole isolation boundary in a public multi-user service.

### `conversation_state.py` — persisted conversational memory

`ConversationState` stores:

- `summary`: Gemini-generated compact summary of older turns.
- `recent_turns`: recent question/answer pairs plus whether each represented a data analysis.
- `last_analysis`: the latest successful analysis question, code, result, and answer.
- `storage_path`: local JSON file path (not serialized as a field).

`load()` tolerates absent or malformed files by starting fresh. `save()` writes to a temporary sibling file and renames it, reducing risk of partial JSON if interrupted. `clear()` resets memory and removes the corresponding state file. `to_analysis_prompt_text()` includes actual analysis turns and instructions not to inherit casual personal context as a filter. `add_turn()` saves turns and, above the configured limit, asks Gemini to summarize the older half. If summarization fails, the turns are retained rather than discarded.

The state key depends on the dataset path, not its contents. The same path reuses state even if the file changes; moving or renaming a dataset creates a different state key.

### `llm_clients.py` — provider SDK boundary

This module contains direct calls to Groq, Mistral, and Gemini. It keeps provider SDK details out of routing and analysis logic.

- `_retry()` performs bounded retries for recognized transient errors.
- `_mistral_completion()` makes chat completion calls, with JSON mode for the router.
- `call_conversation_llm()` and `classify_message()` use the configured 8B model.
- `call_explanation_llm()` uses the configured 14B model.
- `call_fallback_llm()` uses Mistral Medium.
- `call_analysis_llm()` uses Groq first and fails over to Mistral on a retryable Groq outage/limit.
- `call_memory_llm()` uses Gemini chat `send_message` to summarize old turns.

**Why centralize provider calls:** model identifiers, SDK request formats, retries, and fallback can be understood or changed in one place.

### `config.py` — environment-backed settings

Loads `.env` with `python-dotenv`, exposes the provider keys and model IDs, and sets limits for retries, execution, samples, result size, debug output, memory turns, and summary length. Environment variables can override defaults. API keys should remain in `.env` locally or a secret manager in deployment; do not commit them.

### `prompts/` — model instructions

- `request_router.txt`: route definitions and the no-default-filter rule; asks for JSON.
- `conversation_response.txt`: general chat constraints and use of conversational context.
- `code_generation.txt`: require exact columns, a `result` variable, and no intentional file/network/plot actions; defines filter and follow-up behavior.
- `final_response.txt`: explain the execution status and result without making up numbers.
- `analysis_explanation.txt`: explain the stored computation in a verifiable way without exposing hidden reasoning.
- `summarization.txt`: preserve relevant goals, facts, results, and open threads within a word limit.

Prompts are application inputs, not a substitute for validation. Generated code is still checked by the executor, and model output must not be trusted as executable without that check.

### `requirements.txt` and `.gitignore`

Dependencies include pandas/numpy for local data operations, openpyxl for common Excel formats, `python-dotenv` for configuration, and the Groq, Google GenAI, and Mistral SDKs. `tzdata` supports timezone data on systems that need it.

`.gitignore` excludes `.env`, uploaded datasets, `.databuddy_state/`, Python bytecode, and virtual environment directories. Review the ignore rules before publishing; saved user data and real keys should not enter a Git commit.

## 6. Conversation memory behavior

Conversation state is loaded when DataBuddy starts and saved as turns arrive. `/state` prints the summary and recent turns; it does not print the structured `last_analysis` object directly. A full state reset is per loaded dataset path.

The local special case is only for a message with `remember` or `keep in mind` and no question mark. Other personal statements are handled by the chat router/model, then saved as ordinary conversation. This is why statements such as “my name is Snehal” can later be recalled from the conversation context.

When `len(recent_turns)` rises above `MAX_RECENT_TURNS`, DataBuddy sends older turns plus the existing summary to Gemini. With the default threshold of six, the seventh added turn starts a fold. Roughly the older half is replaced with the new summary while the rest remains recent. If Gemini errors, all turns stay saved and the fold can be retried on a later turn.

Only recent turns are explicitly filtered for analysis follow-ups. The summary is general conversational context and may contain user facts; prompts tell models not to treat casual facts as filters, but this relies partly on instruction following.

## 7. Running DataBuddy

Use Python 3.10 or newer. From the project directory in PowerShell:

```powershell
python -m pip install -r requirements.txt
```

Create a private `.env` file with the keys needed by the features you plan to use:

```text
GROQ_API_KEY=your-groq-key
MISTRAL_API_KEY=your-mistral-key
GEMINI_API_KEY=your-gemini-key
```

Start the app with a CSV or Excel path:

```powershell
python app.py uploads\Superstore.csv
```

The app prints the file name, row count, and column count, then accepts requests. DataBuddy loads the whole file into memory at startup. `/quit` exits but leaves saved state in place. `/state` displays conversation context. `/reset` clears the saved state for the current dataset.

## 8. Configuration reference

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | unset | Authenticate primary data-analysis calls. |
| `ANALYSIS_MODEL` | `openai/gpt-oss-120b` | Groq model used for code generation and final analysis answer. |
| `MISTRAL_API_KEY` | unset | Authenticate router, conversation, explanation, and fallback calls. |
| `MISTRAL_CHAT_MODEL` | `ministral-8b-latest` | Router and general conversation. |
| `MISTRAL_EXPLANATION_MODEL` | `ministral-14b-latest` | Explain last analysis. |
| `MISTRAL_FALLBACK_MODEL` | `mistral-medium-latest` | Analysis fallback after Groq temporary failure/limit. |
| `GEMINI_API_KEY` | unset | Authenticate conversation summaries. |
| `MEMORY_MODEL` | `gemini-3.6-flash` | Gemini summary model. |
| `DATABUDDY_TIMEZONE` | `Asia/Kolkata` | Timezone for local clock answers. |
| `MAX_CODE_RETRIES` | `2` | Extra generated-code attempts after execution errors. |
| `EXEC_TIMEOUT_SECONDS` | `5` | Maximum executor runtime for each generated-code attempt. |
| `SAMPLE_ROWS` | `3` | Dataset rows included in the profile prompt. |
| `MAX_RESULT_ROWS` | `20` | Maximum Series/DataFrame rows represented in the result. |
| `MAX_RESULT_CHARS` | `2000` | Maximum result text length before truncation. |
| `DEBUG` | `false` | Print routes, prompts, generated code, and execution details. Can expose data samples and personal conversation context in terminal logs. |
| `MAX_RECENT_TURNS` | `6` | Recent-turn count before summary folding starts. |
| `SUMMARY_MAX_WORDS` | `250` | Requested maximum size of the Gemini summary. |

Model aliases ending in `latest` may point to a newer provider model later. Confirm current provider model availability if an API begins returning an invalid-model error.

## 9. Debugging and testing

Set debug mode in PowerShell for a run:

```powershell
$env:DEBUG = "true"
python app.py uploads\Superstore.csv
Remove-Item Env:\DEBUG
```

Debug output can show prompts, sample rows, recent conversation, generated code, and computed results. Do not share debug logs without checking them for sensitive content.

Useful manual checks with Superstore include:

- General greeting or a question about a fact stated earlier.
- `What is the total Sales across all rows?` Expected CSV total: about 2,297,200.86.
- `How did you calculate that?` after analysis; should explain the saved code/result.
- `Remember that my target region is West.` Then ask for total Sales with no filter; it should still include all rows.
- `What time is it?` It should be handled locally.
- `/state`, then restart with the same dataset to check persistence; `/reset` clears it.
- Several turns beyond `MAX_RECENT_TURNS` to invoke Gemini summary folding.

Provider-backed checks consume API requests and can be blocked by provider rate limits. In particular, an actual fallback test requires Groq to fail transiently and Mistral Medium to be available at that moment. There is not currently an automated test suite in the repository.

## 10. Known limitations and work still planned

- **Frontend:** current user interface is command-line only. A browser-based or desktop chat interface has not been built.
- **Quota monitoring:** there is no mid-session usage polling or early warning. Fallback waits for a Groq failure.
- **Fallback availability:** providers can rate-limit independently; Mistral Medium may be unavailable when Groq is unavailable.
- **Execution isolation:** executor restrictions are useful guardrails but not a hardened sandbox for untrusted code.
- **Privacy:** profile samples and conversational context can be sent to external providers as described above. `DEBUG` can expose these locally in logs.
- **Heuristic routing:** if Mistral routing fails, local word/column matching is best effort and can misclassify an ambiguous message.
- **Date inference:** date detection is based on a small sample and pandas heuristics; mixed formats may warn or parse inconsistently.
- **Excel engine coverage:** installed dependencies clearly cover `.xlsx`; less common Excel formats can require extra pandas reader engines.
- **Large files:** the data is loaded fully into memory. A 500,000-row profile-size/performance check has been deferred; the profile includes a fixed number of rows but the local DataFrame itself still scales with input size.
- **Deferred validation:** retry behavior, unsafe-code rejection/timeout cases, and privacy checks with `DEBUG` have been left for a dedicated test pass.
- **Personal data retention:** chat turns and analysis evidence persist locally until `/reset` or manual removal of the state file. They may also be included in provider prompts for routing, summarization, or answer writing.

## 11. Suggested GitHub README structure

This guide can be condensed into a public-facing README with these sections:

1. Project summary and one-sentence purpose.
2. Short architecture diagram.
3. Features and supported file types.
4. Setup and environment variables (names/placeholders only; never real keys).
5. Run instructions and a short example session.
6. Provider roles and which content each provider receives.
7. State commands and persistence behavior.
8. Security and privacy limits, including the executor caveat.
9. Testing status and known limitations.
10. Future work: frontend and quota monitoring.

Before publishing, ensure `.env`, `.databuddy_state/`, uploads, and any personal sample data are excluded from Git. Review the exact privacy statement carefully so it does not imply that no dataset-derived values leave the computer: the current profile includes example cell values.

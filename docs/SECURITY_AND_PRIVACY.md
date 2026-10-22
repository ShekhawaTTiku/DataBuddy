# Security and privacy

## Intended use

Trusted, non-sensitive personal demonstrations. These safeguards reduce obvious accidental file/network behavior and resource misuse. They do not make generated Python safe for arbitrary public users. The worker shares the host OS account and has no OS-enforced memory or network isolation; AST restrictions are not a complete security boundary.

## Implemented safeguards

- CSV/XLSX only, maximum 20 MiB per upload; processing caps cover rows, columns, CSV cell length, workbook expansion, profiles, questions, context, generated code, result text, chart JSON and worker pipes.
- Failed replacement preserves the working dataset. Uploaded bytes are parsed in memory and never saved by the loader.
- Shared code checks reject obvious file/network methods, private attributes, arbitrary imports and eval/query paths. Worker imports are explicitly permitted rather than enabling unrestricted __import__.
- Worker starts with isolated Python mode, a fresh temporary working directory and a minimal environment without application API keys. It does not import config.py or search for .env.
- Hard worker timeout; bounded stdout/stderr; bounded print capture; validated JSON replies. Parent-created pickle input is private internal transport, never a supported upload, and no worker pickle output is loaded by the parent.
- Chart images/external geographic resources are rejected by basic validation. This is not a comprehensive browser/network sandbox.
- Dynamic filename/suggestion HTML is escaped; columns use native table rendering. Model answers use normal Markdown without unsafe HTML.
- .env variants and .streamlit/secrets.toml are ignored. .env.example contains placeholders. Provider errors exclude raw response bodies, and debug output excludes raw prompts/rows/results.

## What reaches model providers

Groq analysis generation receives a clipped profile with names/types, statistics, low-cardinality values and up to SAMPLE_ROWS real rows, the question and relevant recent analysis. Final-answer writing receives computed evidence, question and context. Mistral routing/chat receives column names/question/context; code and narration fallback receive the corresponding Groq prompt. Prior-analysis explanations include saved session evidence. Chart narration is based on bounded plotted evidence. Gemini memory receives bounded question/answer exchanges, status and computed result text; compression receives the old paragraph and six notes. Mistral receives the same memory payload if used as fallback. The memory engine is not separately given the full DataFrame, profile or code, but conversation and results can contain dataset information.

Memory prompts label their payload as untrusted data. Generated notes and paragraphs are fallible context, never calculation evidence or automatic filters. They are not supplied to code-generation analysis context. Google documents that free-tier content may be used to improve products; use non-sensitive demo data only. See [Google pricing and free-tier disclosure](https://ai.google.dev/gemini-api/docs/pricing). No provider account or privacy settings were changed.

Setting SAMPLE_ROWS=0 removes sample rows only, not all derived data. Never claim that no dataset information leaves the application. Provider retention/account policies must be reviewed before changing the intended data sensitivity or audience. No account privacy settings were inspected or changed in this work.

## Session lifecycle

DataFrames, conversation context and UI uploads live in process/session memory. Reset clears conversation/chart memory, including the rolling paragraph, brief notes and memory notice; Remove dataset clears active app state and rotates the uploader widget. Closing a browser does not guarantee immediate server-memory release; Streamlit eventually discards disconnected sessions. The project creates no durable upload, chat database or saved conversation history. Old .databuddy_state files copied with the backup are ignored, never loaded and were not deleted.

Runner DataFrame/code files exist briefly in a unique temporary directory and are removed after success, failure or timeout. A hard host crash or power loss can prevent normal cleanup. Operating-system swap/crash dumps and provider retention are outside the app's deletion guarantee.

## Downloads and remaining limits

HTML downloads include plotted values and load Plotly from its CDN; disclose this before sharing a chart. PNG export runs in the browser. Dependencies, provider quotas and model availability can change. A 20 MiB file can use substantially more memory after parsing/copying, so free hosting capacity is not guaranteed. No public deployment or hardening certification is implied.

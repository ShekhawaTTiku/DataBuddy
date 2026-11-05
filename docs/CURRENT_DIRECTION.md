# Current direction and recovered decisions

Current status as of 2026-11-05. The owner renamed the current repository to public [ShekhawaTTiku/DataBuddy](https://github.com/ShekhawaTTiku/DataBuddy). The frontend is deployed at `https://databuddy-demo.pages.dev`, the Render API accepts that origin, and browser sample loading passed. Linux container checks passed earlier. Hosted provider streaming and idle-wake acceptance remain pending. See [current deployment details](WEBAPP_SETUP.md#deployment). The dated sections below retain the earlier decisions and checks.

Updated: 2026-10-26 (Asia/Kolkata). This note records the owner's existing decisions, recovered from accessible project chats and current documentation. Subsequent accepted design decisions are in the [dedicated web app design brief](WEBAPP_DESIGN_BRIEF.md). The owner subsequently authorized the complete web implementation; commit, push and deployment remain separate actions.

## Purpose

DataBuddy is the owner's portfolio showcase for personal demonstrations to friends and recruiters. The owner already deployed the earlier Streamlit interface and now wants a dedicated web application with polished, modern UI/UX. The existing Python analysis core was stabilized specifically to support that next stage.

The separate frontend/API was deferred during foundation repairs, not ruled out for the intended dedicated web app. Earlier statements such as "no new frontend/API" describe that completed repair stage. They should not be used to restart settled product questions or treat another Streamlit deployment as the objective.

## Decisions to carry forward

- Zero operating budget; no paid infrastructure or provider upgrades assumed.
- Trusted, ordinary demonstration data; a small showcase audience rather than an enterprise service.
- Maximum upload 20 MiB; CSV is the primary demo format, with existing first-sheet XLSX support retained.
- Dataset and conversation state remain temporary and session-only. No database, accounts, saved datasets or persistent chat history unless the owner later changes scope. Browser close does not guarantee immediate server-memory release.
- Reuse the verified analysis, chart, provider and memory logic. Preserve computed evidence, partial-success behavior, resets and dataset replacement.
- Groq handles code and result narration; Gemini handles memory; Mistral handles routing/chat/explanations and backs up Groq/Gemini. The verified default code fallback is Ministral 14B, superseding earlier Medium proposals.
- Memory uses brief exchange notes, six-exchange rollover into one replacement paragraph, plus bounded recent full exchanges and chart context.
- Work only in `D:/projects/databuddy 2.0`; `D:/projects/DataBuddy` remains the original backup.
- Maintain focused documentation and WORK_LOG.md. Never save credentials, private rows, raw conversations or provider response bodies in project documentation.
- Basic execution checks are not a hardened security sandbox. Address actual hosting/exposure requirements when selecting the architecture without automatically expanding this portfolio demo into enterprise infrastructure.
- Commits, pushes and deployment require explicit authorization for the relevant action. Previous checkpoint authorization is historical, not permission to publish future work.

## Completed stage

Foundation repairs, independent review, provider/memory implementation, real Superstore/browser acceptance and the private GitHub checkpoint are complete. The latest recorded full offline suite passed 152 tests; the live acceptance completed twelve exchanges including both memory rollovers. These are historical results, not a fresh test run on this note's date.

See [changes explained](CHANGES_EXPLAINED.md), [live verification](LIVE_VERIFICATION.md), [provider and memory behavior](PROVIDERS_AND_MEMORY.md), and [GitHub checkpoint](GITHUB_CHECKPOINT.md).

## Current implementation stage

Updated 2026-10-30: the owner retained Cloudflare Pages + Render and authorized incremental answers plus file-by-file publication to DataBuddynew. Streamed ordinary chat/narration, early verified results, reconnect/reload recovery, explicit Stop and preserved memory/accounting are implemented; see [streaming](STREAMING.md). No hosting change or deployment is included. Original web implementation history follows.

Updated 2026-10-27. The owner authorized finalizing the stack and building the full working version, requested less text clutter and invoked frontend-design, React best practices, Web Interface Guidelines and Playwright.

The React/TypeScript/Vite frontend and FastAPI API are implemented around the existing core. Real upload, sample data, chat, charts, evidence, exports, temporary sessions and adaptive allowance are connected. See [working setup/deployment](WEBAPP_SETUP.md), [verification](WEBAPP_VERIFICATION.md) and [design notes](WEBAPP_DESIGN_NOTES.md). No new accounts, database or persistent chat history were added.

Updated 2026-10-30 after the owner's WSL restart: Docker is installed, the production image builds on Linux, all 183 Linux tests pass and local 512 MiB/no-swap/0.1-CPU probes plus production startup/restart smoke checks pass. See [container verification](CONTAINER_VERIFICATION.md); these checks did not change application code or consume provider quota.

The next stage is actual deployment acceptance when authorized: Cloudflare/Render URLs, private secret configuration, hosted cold wake-up, streaming/proxy/browser checks and current provider behavior. Local WSL2 limits do not certify Render performance, every allowed upload or multi-session resource peaks. The accidental Sites request remains cancelled. No commit, push or deployment occurred in this container-verification task.

## Recovery sources and limits

Reviewed accessible DataBuddy chats: "Precheck DataBuddy web app migration", "Summarize changes so far", "Study the project thoroughly", "Diagnose Streamlit app startup", "Mistral AI addition", "studying databuddy", and "DataBuddy v2.0". Also reviewed the relevant portfolio discussion in "live", where DataBuddy was selected for a full UI/UX showcase. Current documentation takes precedence over superseded implementation descriptions in older chats.

The older linked ChatGPT conversation "Explain DataBuddy README" could not be retrieved because its host was unavailable. This note therefore does not claim exhaustive access to every historical conversation. No raw conversation transcripts were copied into the repository.

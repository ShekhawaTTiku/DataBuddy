# Chat and dataset lifecycle

Updated 2026-11-05. DataBuddy supports model-backed conversation before loading a dataset. The same session token, response job, stream, Stop/reconnect handling, bounded memory and message allowance serve both general conversation and dataset work.

## Before a dataset is loaded

The existing Mistral conversation model receives the message, bounded conversation context, actual app capabilities, dataset availability and the configured server clock. This path makes no dataset-routing, code-generation or calculation call. It can greet users, respond to introductions and corrections, recall user-provided facts, explain app features and discuss general concepts.

The prompt asks the model to handle the whole message. A greeting combined with a sales calculation request should invite an upload or sample. It must not invent a loaded dataset, computation or previous chart. It should distinguish a name introduction from a sentence such as “I'm having trouble uploading”, and follow later explicit name corrections. These are model-guided behaviors and can still be misinterpreted.

Upload data and Try sample data remain available after the initial welcome screen becomes a conversation. Simple greetings should receive concise answers without repeating upload instructions in every reply.

## Upload, reset and removal

| Action | Conversation and memory | Message allowance |
| --- | --- | --- |
| First successful upload or sample | Preserved, including introductory names/preferences | Preserved |
| Invalid upload | Existing chat and dataset remain available | Preserved |
| Replace an existing dataset | Cleared after successful replacement | Preserved |
| Clear chat | Cleared, including remembered personal facts; dataset retained | Preserved |
| Remove dataset | Dataset, chat, analysis/chart evidence and memory cleared | Preserved |
| Expired session or server restart | Previous in-memory state is unavailable | New session policy applies |

The first upload preserves the existing ConversationState object. A later dataset replacement creates fresh state. Personal facts and summaries remain separate from the calculation context, so a casual reference to a region does not silently become a filter.

## Usage, failure and delivery

All admitted model-backed messages count toward the existing allowance, initially 15. Greetings use provider quota too, and the existing one-time allowance adjustment remains in effect. Each completed exchange uses the existing six-note memory cycle. No database or persistent chat history is added.

Duplicate request IDs attach to the original request. Stop and reconnection reuse the existing response delivery. Provider failures are shown as failed or partial responses without discarding completed calculation evidence. Backend sleep, cold starts and free-provider limits still apply.

## Verification

The offline suite covers provider dispatch before upload, prompt state, context, duplicate submissions, validation, allowance exhaustion, failures, first-upload preservation, invalid uploads, replacement, reset and removal. Real-socket streaming/reconnect/Stop checks run with and without a dataset. Regression tests block external provider connections.

`scripts/verify_chat_ui.js` verifies the local browser flow against `scripts/browser_fixture.py`. `scripts/verify_streaming_ui.js` checks incremental answers, early charts, Stop, reconnect, mobile layout and accessibility. Screenshots use synthetic content and stay under ignored `output/playwright`.

`python scripts/verify_live_chat.py --live` explicitly enables real provider calls against a local API. Add `--base-url https://databuddynew.onrender.com` for the approved hosted API. It uses synthetic questions and sample data and prints aggregate pass/fail checks. It does not print model response bodies or credentials. See the dated [work log](WORK_LOG.md) for results.

For the hosted browser check, first run `python scripts/verify_live_chat.py --write-browser-fixtures` to create synthetic CSV/XLSX inputs under ignored output; this command uses no provider quota. Open the approved Pages site in a fresh Playwright CLI session, then run `playwright-cli run-code --filename scripts/verify_hosted_chat_ui.js` from the checkout. This opt-in callback uses nine real model-backed submissions, checks the first-upload/name lifecycle, actual calculations/charts, PNG/HTML downloads, reload, Stop and narrow layouts, and rejects browser console errors. Run only with provider-usage authorization. Existing test sessions count toward the four-session capacity until expiry or restart.

Basic calculation checks and Docker packaging remain **not a hardened security sandbox**. This application is a trusted personal demonstration.

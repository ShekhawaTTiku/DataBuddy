# Incremental answers and response recovery

Implemented 2026-10-30 for the existing React/FastAPI application. Hosting remains Cloudflare Pages plus conditional Render Free. No new service, account, database, paid dependency or persistent conversation storage is introduced. The existing 20 MiB upload ceiling and provider/model roles remain.

## What the user sees

For a data question: Mistral classifies the request, Groq prepares code, Python calculates, verified results become available, and Groq's explanation appears progressively. Chart interpretation and explanations of earlier analyses also stream. Ordinary chat uses Mistral. Short local clock/remember replies can appear immediately. Routing, generated code and Gemini memory are buffered internally; Calculation remains available for inspecting completed analysis code.

The answer is readable before memory finishes. Send stays disabled while the existing bounded memory update and final accounting complete. Gemini still creates one brief per exchange, combines the sixth with the five previous notes and old paragraph, and replaces the paragraph. Mistral retains its existing memory fallback. No memory request is made for individual text chunks.

With a dataset loaded, dedicated-web-app routing classifies without answering, followed by a separate streamed chat request for ordinary conversation. Before upload, the new chat path calls the model directly without routing. The Streamlit/terminal paths retain buffered answers and their combined router/chat behavior. Streaming improves when reading can start; it does not speed Python calculation or guarantee lower token usage. The application allowance remains an estimate, not a provider-quota promise.

## Transport and bounds

- POST `/api/messages` keeps the existing request-ID admission and one-message charge. It starts one background job.
- Authenticated GET `/api/jobs/{id}/events` uses `text/event-stream`, consumed with fetch and the existing bearer header. Tokens never appear in URLs. Sessions cannot subscribe to another session's job.
- Events contain current bounded answer snapshots and real stages. Updates are coalesced at approximately 50 ms; this is genuine progressive provider output rather than simulated typing of a finished answer. Ready evidence is sent on attachment/change, not repeated with every answer fragment. Snapshots avoid an unbounded token replay log.
- Ten-second comment heartbeats support idle detection. The frontend has a 35-second connection/inactivity watchdog, aborts readers on cleanup, and reconnects with a short delay. It checks the existing job/session endpoints when delivery fails; reconnecting never submits the question again.
- Current answer text retains the 6,000-character cap. Chart, table, worker and prompt bounds remain. The frontend rejects event frames above 4.5 million characters, allowing bounded JSON-escaped chart/table evidence. At most two stream subscribers may attach to the current job. Slow readers do not block the calculation worker.
- The existing one-operation gate, one API worker, four-session cap and session expiry still apply. No Redis, message broker, WebSocket service or shared session store is required.

`backend/core/response_stream.py` supplies request-local delivery/cancellation through a ContextVar. `backend/api/streaming.py` holds only the current in-memory job snapshot. The core remains usable without delivery; `DataBuddy.ask` remains the one conversation/memory recording path. The API owns one display-turn/usage finalization per admitted request.

## Interruptions and Stop

A broken browser connection detaches the reader while the existing bounded job continues. Reattachment receives the current snapshot and subsequent updates. Completing or reconnecting does not repeat provider work or charge another message. Reset/removal/replacement clear current delivery along with the existing dataset/conversation lifecycle and remain blocked during active work.

Temporary Groq narration failures retain existing bounded Mistral fallback. If primary text was already visible, an explicit restart notice clears the unfinished draft before the backup begins. The saved computation is reused; Python is not rerun. Permanent configuration failures do not silently switch providers. A broken Mistral answer remains clearly partial; Mistral cannot back up itself. Only answer content is forwarded, not provider reasoning/debug fields.

Stop calls POST `/api/jobs/{id}/cancel`. It signals the server, best-effort closes active provider IO and kills/reaps a running calculation child at the next cancellation check. The UI says Stopping until the request settles. SDK/network shutdown can still take time within existing timeouts; an HTTP disconnect alone is not cancellation. No further answer-generation retries/fallback occur after cancellation. Completed evidence and partial text survive, with an explicit stopped status.

One accepted stopped exchange still uses one message. It records one status-aware brief and participates in the existing six-exchange memory cycle; this bounded memory request can run after Stop. Already consumed provider quota cannot be refunded. Completion/Stop races settle through the single worker/finalization path, without a second turn or memory update.

Usage reports are retained once per provider attempt, including fallback and memory. Final/cumulative stream metadata is not summed per chunk. Failed/interrupted attempts with missing usage make totals incomplete and do not trigger allowance reductions from incomplete observations. Groq's existing allowlisted quota headers remain available. No raw provider bodies or generated content are added to telemetry or disk logs.

Exactly-once bookkeeping is limited to a live in-memory session. Provider timeouts can consume unreported quota. Process restart/expiry loses session state and requires the existing new-session/reupload flow; the app does not automatically replay an unknown lost job.

## Verification and hosting

Use the normal provider-free Python suite and frontend tests/build. `tests/test_streaming.py` includes real installed-SDK serialization through fake HTTP transports plus a local Uvicorn/socket check proving a partial answer is delivered before completion. The synthetic browser fixture and `scripts/verify_streaming_ui.js` exercise incremental UI, reload recovery, Stop, fallback replacement and early charts without live providers. See [verification](WEBAPP_VERIFICATION.md) for recorded outcomes.

For the isolated browser check, start the fixture on 8001 and Vite on 5174 as described in [setup](WEBAPP_SETUP.md), then run `playwright-cli run-code --filename scripts/verify_streaming_ui.js`. The callback verifies fixture identity and blocks non-fixture API traffic before submitting. It suppresses the existing unsaved-work browser confirmation in its test page so reload recovery can be automated. Screenshots use synthetic content under ignored output paths.

The Docker allowlist includes the core delivery module. The [local Linux container/resource checks](CONTAINER_VERIFICATION.md) pass, including the regression suite's real loopback streaming check. Hosted acceptance on application release `6ea1910` observed progressively delivered text in seven of ten actual-provider requests through the Render API. A later actual-browser check on backend `d9854cd` observed two progressive rendered states and resumed during active-work reload with one submission, charge and finalized turn. Event responses send no-store/no-transform and X-Accel-Buffering: no. These observations do not certify every proxy condition, cold wake, outage or high-load workload. See [current verification](WEBAPP_VERIFICATION.md) for browser recovery/Stop results. Basic execution checks and Docker packaging are **not a hardened security sandbox**.

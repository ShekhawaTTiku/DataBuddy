# Working web app and deployment handoff

Updated 2026-11-06 (Asia/Kolkata). The current public source repository is [ShekhawaTTiku/DataBuddy](https://github.com/ShekhawaTTiku/DataBuddy), renamed by the owner from DataBuddynew. Local `main` tracks `origin/main`. The frontend is deployed at `https://databuddy-demo.pages.dev` and the API runs on Render Free. See [deployment](#deployment) for verified behavior and remaining hosting limits.

## Chat before upload

Messages without a dataset use the existing Mistral conversational model directly, with actual app capabilities, dataset availability, server time and bounded session context. They stream through the same job, cancellation, reconnect and accounting flow as dataset responses. Every submitted model-backed message counts toward the existing allowance, including greetings. Memory uses the same six-exchange cycle.

The first successful CSV/XLSX upload or sample selection preserves prior chat and memory. Invalid uploads preserve them too. Replacing an existing dataset, removing it or clearing chat resets the relevant conversation memory while preserving the used allowance. General chat never invokes dataset calculations while no dataset is loaded. App-help replies explain upload/sample actions, and both actions remain available after the welcome screen is replaced by chat.

Python source is grouped under `backend/api`, `backend/core` and `backend/legacy`; prompts live beside the core. Dependency manifests live under `requirements`. Use `python -m backend.cli` for the terminal interface and `uvicorn backend.api.main:app` for the API. Root `app.py` and `web_app.py` remain compatibility launchers. The local private `.env` remains at the repository root and is excluded from Docker.

## Final stack

- React 19.3.1 + TypeScript 7.0.2 + Vite 8.3.5.
- Custom CSS theme tokens, locally bundled DM Sans/Newsreader and Lucide icons. Adapted Vercel AI Elements conversation/message primitives use `use-stick-to-bottom` 1.1.6. Streamdown 2.7.1 with math/Mermaid plugins renders answers; Tailwind 4.3.3 generates only the renderer's utilities without a global CSS reset.
- Plotly.js 4.1.2 through react-plotly.js 4.1.0, loaded when a chart is needed. Standalone HTML export loads its additional source asset only on request.
- Python 3.11, FastAPI 0.143.0 and Uvicorn 0.54.0. Existing pandas/NumPy/openpyxl/Plotly analysis and Groq/Gemini/Mistral roles retained.
- Temporary in-process sessions, no database or accounts. Docker packages the API. Cloudflare Pages Free + Render Free host the deployed app.

`frontend/package-lock.json` locks the browser dependencies. `requirements/api.txt` lists direct Python dependencies; `requirements/api-lock.txt` pins the 47-package tested runtime closure used by Docker. The legacy Streamlit application remains available separately.

## Run locally

From the working checkout, using Python 3.11:

```powershell
python -m pip install -r requirements/api-lock.txt
# If .env does not already exist, copy .env.example and fill in keys privately.
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to port 8000. Leave `VITE_API_URL` empty for this local setup. The sample button loads four synthetic rows without consuming provider quota. Sending a question uses the configured providers. Never put provider keys in frontend variables.

For a local production-build preview, run `npm run build` then `npm run preview`. Include `http://127.0.0.1:4173` in the API process's `DATABUDDY_ORIGINS` before starting it. Restart the API after changing origins. Preview also uses the configured local proxy.

## Working behavior

Upload CSV/XLSX (first worksheet), inspect the preview, choose a suggested task, ask questions, read answers, inspect computed tables/calculation code, open interactive charts, and download PNG or self-contained HTML. Chart previews are static in chat; the analysis panel enables interaction. The panel is a focus-managed dialog, full screen on mobile. Partial results preserve charts and evidence when narration fails. Clear chat, remove dataset and replacement require confirmation and preserve usage allowance.

The sidebar links to exchanges in the current conversation; it is not a saved-chat database. The UI shows short instructions, not the explanatory copy from the earlier mockup. Light/dark colors live in `frontend/src/styles.css`.

The five task buttons now open dataset-aware question menus on hover, keyboard focus or tap. Choose a question to place its full editable text in the prompt; only Send submits it. Menus stay open while moving from the trigger into their choices, close with Escape/outside interaction, and support arrow keys, Home/End and type-ahead. They scroll when space is limited and fit narrow screens. All generated choices are shown up to ten; larger sets show “Top 10 suggestions.” Menus stay available after responses, including “Chart the previous result” when computed evidence exists, and are disabled during work or at allowance exhaustion.

Suggestions are computed locally from cached per-column types, distinct/missing counts and identifier flags, calculated once per successful dataset load. No cell values or extra provider requests are needed. Date trends use actual parsed date columns; absent dates or group columns produce explanatory empty states. Empty/constant columns, recognized identifier names and high-cardinality text are excluded from analytical choices. Group suggestions use at most 30 distinct values. Ranking and total-versus-average choices are conservative heuristics based on column names/types; review/edit a proposed question when your dataset uses different semantics. Replacement refreshes the menu facts; failed replacement preserves them, Clear chat keeps them, and Remove dataset clears them.

Conversation history has a full-width scroll viewport above the prompt. New content follows the bottom until the user scrolls up; Latest message restores following. Reload starts at the latest exchange, including late-loaded charts. Autofocus runs after connection, reset, dataset readiness and exchange navigation, including touch devices as requested. It does not repeatedly steal focus during usage/detail interaction.

Charts retain their generated height with per-row/per-column minimums for Cartesian dashboards, label margins and a separate title/legend area. Multi-panel previews and interactive charts use a readable minimum canvas width; narrow containers scroll horizontally. Interactive chart panels are wider on desktop. PNG and self-contained HTML exports use the same readable geometry. Generated chart prompts also request generous subplot spacing. This is a layout safeguard, not a guarantee that arbitrary generated figures or very long labels need no further adjustment.

Streamdown handles progressive answers, tables, code copy/download controls, local KaTeX equations and strict-mode Mermaid diagrams. Raw HTML and embedded Markdown images remain disabled. The API now delivers incremental chat/explanation text through authenticated fetch/SSE. Verified result data/charts can appear before narration finishes, and answers stay readable during the subsequent memory update. Send remains disabled until finalization. Stop cancels server work, preserves completed evidence and records one explicitly stopped exchange; its bounded memory update still runs. Reconnect/reload attaches to the existing job without resubmission. Ordinary web chat now uses separate routing and answer calls. See [streaming and recovery](STREAMING.md) for bounds, fallback, accounting and limitations.

## Session and request policy

- Random bearer token in tab-scoped `sessionStorage`; dataset/chat/usage remain in server memory. No private content in localStorage. Without browser storage, the token remains in memory until reload.
- As requested, non-sensitive display preferences (theme, desktop sidebar and last selected analysis tab) use allowlisted localStorage values across reloads/new sessions. Explicit Chart/Result data/Calculation actions select their named view. Corrupt/blocked storage falls back safely. There are no model-selection, web-search or reasoning controls in this version; provider/model routing remains server configured.
- 30 minutes of API inactivity expires a session. Cleanup runs every minute and before session lookups. Active work is not evicted mid-request. Closing a tab does not immediately clear server state; server restarts clear it.
- At most four resident sessions and one upload/analysis operation at a time. Requests beyond capacity get actionable busy feedback. Run exactly one Uvicorn worker and one service instance: there is no shared session store.
- The 20 MiB upload ceiling remains. Existing row/column/cell/expansion limits apply. Additional admission checks limit a parsed DataFrame to 48 MiB and all retained DataFrames to 72 MiB. These checks happen after parsing; they do not guarantee peak RSS below 512 MB for every allowed input.
- Request bodies and upload duration are bounded. Analysis runs in the existing disposable worker with bounded output/time. Actual progress stages are polled via the small `/api/job` response; full results are fetched once on completion.
- A request ID prevents duplicate application jobs/message charges on resubmission. The browser retains the same ID when the outcome of a network failure is uncertain. Streaming reconnect is read-only; an interrupted delivery does not resubmit. Concurrent mutations remain blocked while the answer and memory are running. This does not guarantee zero provider consumption after an ambiguous provider timeout.

## Allowance and usage

15 accepted messages per session. Validation and capacity rejections do not count; accepted submissions including greetings, errors and partial results count once. Clearing chat, removal, replacement and reload do not replenish the allowance. A new/expired browser session can obtain another allowance: this is a demo policy, not durable per-person abuse prevention.

Input feedback estimates UTF-16 text length / 4, warning above 600 estimated tokens. This is deliberately labeled approximate; it is not a provider tokenizer. After three submissions, the server reviews complete provider-reported whole-exchange totals once. Average >12,000 reduces total allowance to 14; >18,000 reduces it to 13. Incomplete metadata skips the reduction. No subsequent repeated deductions; remaining counts never go negative. The output-token cap is separate.

Offline calibration used real prompt builders with synthetic data/responses: three fresh sample exchanges estimated 1,837–2,057 tokens, or 8,725–8,945 when reserving each call's configured maximum output. Long-context cases estimated 9,315, or 16,203 including maximum outputs. The 12,000 baseline is a conservative **application planning threshold** between these envelopes, not measured live average usage or a free-quota guarantee. Reproduce with `python scripts/usage_estimate_check.py`; no provider calls occur.

The Usage control opens on hover/focus or tap. A pointer bridge and short leave delay keep the card open while moving into its details; moving outside both closes it. Keyboard focus stays usable until focus leaves or Escape is pressed; outside taps also close it. It reports observed attempts/fallbacks, provider/model input/output/total tokens, supplied reasoning/cache counts, timestamps, last-exchange/session totals and allowance. Failed calls can have unreported consumption. Totals are explicitly incomplete when metadata is missing. Groq's available response headers supply remaining daily requests, minute tokens and relative reset durations, with timestamps; Gemini/Mistral account quotas remain unavailable. No unlike quota windows are added together.

## Offline checks

```powershell
python -m pip install -r requirements/web-dev.txt
python -m pytest -q
cd frontend
npm ci
npm test
npm run build
```

`scripts/browser_fixture.py` is a **verification-only server** on port 8000. It uses synthetic provider responses, the real loader/API/calculation worker, and blocks external network connections. It is excluded from Docker and is never the production entry point. Browser artifacts use only synthetic content and live under ignored `output/playwright/`. See [verification](WEBAPP_VERIFICATION.md).

For isolated suggestion-menu verification, generate synthetic files with `python scripts/browser_fixture.py --write-ui-fixtures`, then run the fixture with `DATABUDDY_FIXTURE_PORT=8001`. Start Vite separately with `VITE_API_URL=http://127.0.0.1:8001` and `npm run dev -- --port 5174`. The verification callback `scripts/verify_suggestion_ui.js` targets these explicit test ports and refuses non-fixture submissions. Run it from the checkout via Playwright CLI after opening `http://127.0.0.1:5174`. Keep these test-only environment settings out of production frontend builds.

## Deployment

As of 2026-11-06, the public frontend is `https://databuddy-demo.pages.dev`. Render runs backend `d9854cd`; Cloudflare's frontend includes `ff4ae8c`. Render uses `DATABUDDY_ORIGINS=https://databuddy-demo.pages.dev` and privately configured provider keys. The frontend and `/api/health` return HTTP 200, with the matching API CORS header. Earlier hosted API acceptance passed ten submissions including six-exchange memory and progressive delivery. The corrected release passed nine hosted browser submissions plus one active-reload request, covering chat/name behavior, CSV/XLSX lifecycle, actual calculations/charts, exports, Stop and no duplicate charge/turn. The table keyboard fix passed locally and live; inspected WCAG A/AA checks passed. No key values were displayed or published. See [verification](WEBAPP_VERIFICATION.md) and the [recovery checkpoint](PROGRESS.md) for outcomes and remaining limits. Documentation-only pushes may advance Cloudflare's revision while leaving the verified application code unchanged.

1. **Render API:** use the repository root Dockerfile and `render.yaml`, Free plan, one instance. Health path `/api/health`; port comes from Render's `PORT`. Set `GROQ_API_KEY`, `GEMINI_API_KEY`, `MISTRAL_API_KEY` privately. `DATABUDDY_ORIGINS` must be the exact Cloudflare frontend origin, including `https://`, without a path/trailing slash. Multiple approved origins may be comma-separated; wildcard is rejected. `EXEC_TIMEOUT_SECONDS=30` is in the blueprint for the small CPU.
2. **Cloudflare Pages:** project root `frontend`, build command `npm ci && npm run build`, output `dist`, Node 24. Set `VITE_API_URL=https://<actual-render-service>.onrender.com` at build time. Do not append `/api`. This value is public and contains no secret. No Pages Functions, database or paid service is needed.
3. **Origins:** set each side's actual deployed URL and rebuild the frontend after changing its API origin. Cross-origin authorization uses bearer headers rather than third-party cookies. CORS permits only explicit configured origins. It is not authentication or protection against arbitrary non-browser clients.
4. **Headers:** `frontend/public/_headers` supplies Cloudflare CSP, no framing, referrer and browser-permission rules. CSP permits the Render domain family for connections, inline styles, embedded chart-control fonts and Plotly's full distribution evaluation needs. Narrow `connect-src` to the actual API origin when known. A different API domain requires updating CSP too. Provider keys, `.env`, private files, tests and browser fixtures are excluded from the Docker context by an allowlist.
5. **Hosting acceptance:** build/run the image and repeat sample, upload, streaming chat/narration, early chart/result, export, Stop, reconnect, expiry/restart and provider-fallback smoke checks. Verify text arrives through the real proxy before completion and that buffering/compression/timeouts do not accumulate the answer. Run the resource probe inside an equivalent Linux environment with the host's 512 MB/0.1 CPU constraints; validate the 30-second worker limit. Check a cold start and frontend retry feedback. Do not assume the Linux wheel resolution check proves runtime compatibility.

The frontend can load while Render wakes up; the API can sleep after inactivity and may take roughly a minute to return. Waking/unavailable feedback, retry and session-expired/reupload flows are implemented. Free-provider limits and Render resource limits can interrupt a session. No paid fallback is enabled.

## Local container checks and remaining hosting limitation

Updated 2026-10-30: WSL2 and Docker Desktop are installed and working. The existing production image builds on Linux amd64 with all 47 locked dependencies. All 183 Linux regression tests and eight local 512 MiB/no-swap resource probes passed, including at 0.1 CPU; production HTTP startup/restart checks passed too. See [container verification](CONTAINER_VERIFICATION.md) for precise results and reproduction. No application change or upload-limit reduction was needed.

Hosted provider and proxy-stream acceptance now pass for the exercised flows. Free-host idle-wake timing, arbitrary outages, all permitted 20 MiB files, every resident-session combination and sustained load are not certified by these checks. Strict 0.1-CPU processing can be slow. Basic execution checks and Docker packaging are **not a hardened security sandbox**. This remains a trusted portfolio demo.

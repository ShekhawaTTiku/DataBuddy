# Working web app and deployment handoff

Updated 2026-10-27 (Asia/Kolkata). The owner authorized the complete web implementation. It is built locally; no commit, push, hosting service creation or deployment has occurred.

## Final stack

- React 19.3.1 + TypeScript 7.0.2 + Vite 8.3.5.
- Custom CSS theme tokens, locally bundled DM Sans/Newsreader, Lucide icons and safe Markdown rendering.
- Plotly.js 4.1.2 through react-plotly.js 4.1.0, loaded when a chart is needed. Standalone HTML export loads its additional source asset only on request.
- Python 3.11, FastAPI 0.143.0 and Uvicorn 0.54.0. Existing pandas/NumPy/openpyxl/Plotly analysis and Groq/Gemini/Mistral roles retained.
- Temporary in-process sessions, no database or accounts. Docker packages the API. Cloudflare Pages Free + Render Free remain the hosting target.

`frontend/package-lock.json` locks the browser dependencies. `requirements-api.txt` lists direct Python dependencies; `requirements-api-lock.txt` pins the 47-package tested runtime closure used by Docker. The legacy Streamlit application remains available separately.

## Run locally

From the working checkout, using Python 3.11:

```powershell
python -m pip install -r requirements-api-lock.txt
# If .env does not already exist, copy .env.example and fill in keys privately.
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
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

## Session and request policy

- Random bearer token in tab-scoped `sessionStorage`; dataset/chat/usage remain in server memory. No private content in localStorage. Without browser storage, the token remains in memory until reload.
- 30 minutes of API inactivity expires a session. Cleanup runs every minute and before session lookups. Active work is not evicted mid-request. Closing a tab does not immediately clear server state; server restarts clear it.
- At most four resident sessions and one upload/analysis operation at a time. Requests beyond capacity get actionable busy feedback. Run exactly one Uvicorn worker and one service instance: there is no shared session store.
- The 20 MiB upload ceiling remains. Existing row/column/cell/expansion limits apply. Additional admission checks limit a parsed DataFrame to 48 MiB and all retained DataFrames to 72 MiB. These checks happen after parsing; they do not guarantee peak RSS below 512 MB for every allowed input.
- Request bodies and upload duration are bounded. Analysis runs in the existing disposable worker with bounded output/time. Actual progress stages are polled via the small `/api/job` response; full results are fetched once on completion.
- A request ID prevents duplicate charges/calls on resubmission. The browser retains the same ID when the outcome of a network failure is uncertain. Concurrent mutations are blocked while work is running.

## Allowance and usage

15 accepted messages per session. Validation, missing-dataset and capacity rejections do not count; accepted submissions including errors and partial results count once. Clearing chat, removal, replacement and reload do not replenish the allowance. A new/expired browser session can obtain another allowance: this is a demo policy, not durable per-person abuse prevention.

Input feedback estimates UTF-16 text length / 4, warning above 600 estimated tokens. This is deliberately labeled approximate; it is not a provider tokenizer. After three submissions, the server reviews complete provider-reported whole-exchange totals once. Average >12,000 reduces total allowance to 14; >18,000 reduces it to 13. Incomplete metadata skips the reduction. No subsequent repeated deductions; remaining counts never go negative. The output-token cap is separate.

Offline calibration used real prompt builders with synthetic data/responses: three fresh sample exchanges estimated 1,837–2,057 tokens, or 8,725–8,945 when reserving each call's configured maximum output. Long-context cases estimated 9,315, or 16,203 including maximum outputs. The 12,000 baseline is a conservative **application planning threshold** between these envelopes, not measured live average usage or a free-quota guarantee. Reproduce with `python scripts/usage_estimate_check.py`; no provider calls occur.

The Usage control opens on hover/focus and pins on click/tap. It reports observed attempts/fallbacks, provider/model input/output/total tokens, supplied reasoning/cache counts, timestamps, last-exchange/session totals and allowance. Failed calls can have unreported consumption. Totals are explicitly incomplete when metadata is missing. Groq's available response headers supply remaining daily requests, minute tokens and relative reset durations, with timestamps; Gemini/Mistral account quotas remain unavailable. No unlike quota windows are added together.

## Offline checks

```powershell
python -m pip install -r requirements-web-dev.txt
python -m pytest -q
cd frontend
npm ci
npm run build
```

`scripts/browser_fixture.py` is a **verification-only server** on port 8000. It uses synthetic provider responses, the real loader/API/calculation worker, and blocks external network connections. It is excluded from Docker and is never the production entry point. Browser artifacts use only synthetic content and live under ignored `output/playwright/`. See [verification](WEBAPP_VERIFICATION.md).

## Deployment: prepared configuration

No deployment commands below have been executed. Deployment still requires the owner's explicit authorization.

1. **Render API:** use the repository root Dockerfile and `render.yaml`, Free plan, one instance. Health path `/api/health`; port comes from Render's `PORT`. Set `GROQ_API_KEY`, `GEMINI_API_KEY`, `MISTRAL_API_KEY` privately. `DATABUDDY_ORIGINS` must be the exact Cloudflare frontend origin, including `https://`, without a path/trailing slash. Multiple approved origins may be comma-separated; wildcard is rejected. `EXEC_TIMEOUT_SECONDS=30` is in the blueprint for the small CPU.
2. **Cloudflare Pages:** project root `frontend`, build command `npm ci && npm run build`, output `dist`, Node 24. Set `VITE_API_URL=https://<actual-render-service>.onrender.com` at build time. Do not append `/api`. This value is public and contains no secret. No Pages Functions, database or paid service is needed.
3. **Origins:** set each side's actual deployed URL and rebuild the frontend after changing its API origin. Cross-origin authorization uses bearer headers rather than third-party cookies. CORS permits only explicit configured origins. It is not authentication or protection against arbitrary non-browser clients.
4. **Headers:** `frontend/public/_headers` supplies Cloudflare CSP, no framing, referrer and browser-permission rules. CSP permits the Render domain family for connections, inline styles and Plotly's full distribution evaluation needs. Narrow `connect-src` to the actual API origin when known. A different API domain requires updating CSP too. Provider keys, `.env`, private files, tests and browser fixtures are excluded from the Docker context by an allowlist.
5. **Hosting acceptance:** build/run the image and repeat sample, upload, chart, export, expiry/restart and provider-fallback smoke checks. Run the resource probe inside an equivalent Linux environment with the host's 512 MB/0.1 CPU constraints; validate the 30-second worker limit. Check a cold start and frontend retry feedback. Do not assume the Linux wheel resolution check proves runtime compatibility.

The frontend can load while Render wakes up; the API can sleep after inactivity and may take roughly a minute to return. Waking/unavailable feedback, retry and session-expired/reupload flows are implemented. Free-provider limits and Render resource limits can interrupt a session. No paid fallback is enabled.

## Remaining hosting limitation

Docker and WSL are not installed on the current machine. Linux-compatible dependency resolution passed, and local Windows resource probes passed, but the Docker image and real Render workload could not be executed here. This is a deployment acceptance check, not a claim that all 20 MiB datasets fit. Basic execution checks and Docker packaging are **not a hardened security sandbox**; this remains a trusted portfolio demo.

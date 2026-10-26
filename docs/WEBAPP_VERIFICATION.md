# Dedicated web app verification

Date: 2026-10-27 (Asia/Kolkata). All new automated/browser verification used synthetic data and offline provider doubles. No live quota was consumed. Historical live-provider acceptance is recorded separately in LIVE_VERIFICATION.md.

## Automated and build checks

- Full Python regression suite: **167 passed in 35.28 seconds**, including the 152 existing tests and new API/telemetry/result-table coverage. One upstream Starlette TestClient/httpx deprecation warning remains, with no failed checks.
- API checks cover session separation/authentication, explicit CORS, no-store responses, CSV/XLSX loading, invalid and oversized payloads, retained old data after failed replacement, admission limits, expiry, active-work protection, safe errors, duplicate request IDs, reset/remove budget preservation, allowance adjustment/exhaustion, partial results and streamed-body limits.
- Provider instrumentation checked with synthetic SDK response objects and the real Groq SDK using an offline HTTP transport. Numeric usage and allowlisted quota headers are retained; response bodies are not.
- Existing monthly grouping test caught pandas PeriodIndex JSON recursion in the new result-table serialization. Fixed by normalizing table cells/index explicitly. Added focused regressions for period indexes, nulls, infinities and clipped cells.
- `npm run build` passes TypeScript and Vite production bundling. Initial JavaScript is about 372 kB (115 kB gzip); Plotly is a separate lazy chunk about 4.65 MB (1.42 MB gzip). Its roughly 4.83 MB standalone export source is requested only for HTML download. Preserving the existing range of Plotly chart types explains the large deferred chart dependency.
- `npm install` audit: zero reported vulnerabilities. Dependency lockfile included. Linux Python 3.11 wheel-only resolution passed for direct requirements and the exact 47-package API lock. This does not execute Linux code.

## Skill reviews

Applied frontend-design and documented the two-pass design in WEBAPP_DESIGN_NOTES.md. Applied React best practices: event-driven mutations, in-flight startup deduplication, conditional imports, memoized chart thumbnails, locally bundled fonts, and small progress polling rather than repeated chart-history downloads.

Fetched and reviewed the [current Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md). Retained sentence case because the user's invoked frontend-design brief explicitly requests it. Session-only inspection state is not placed in public/shareable URLs; sidebar anchors navigate individual turns.

Findings fixed (source locations can shift as files are formatted):

- `frontend/src/App.tsx` — mobile dataset icon lost its accessible name when text was hidden; added explicit label.
- `frontend/src/styles.css` — dark theme changed tokens but left literal root foreground/background; bind both to theme tokens.
- `frontend/src/Modal.tsx` — backward Tab from the first control could leave document focus; added explicit first/last focus cycling alongside native modal behavior.
- `frontend/src/App.tsx` — avoid automatically opening a mobile keyboard after upload; focus composer automatically only with a fine pointer.
- `frontend/src/App.tsx` — update browser theme-color with the selected theme; long model names wrap in Usage details.
- `frontend/src/api.ts` — startup promise must deduplicate only in-flight calls, not replay stale initial session snapshots after remount; clear it when settled.

Native controls, semantic tables, labels, focus outlines, live error/progress notices, reduced motion, escaped Markdown and confirmation dialogs were reviewed. Axe found no remaining violations in the tested light/dark chat, dataset/result/analysis dialogs and mobile exhausted state. This is a bounded accessibility review, not a full assistive-technology certification.

## Browser flows

Used the requested Playwright CLI wrapper and fresh snapshots, with the actual local production build as well as the development build. Desktop 1440×900, tablet 768×1024, mobile 390×844 and narrow mobile 320×640 were checked; no page-level horizontal overflow in the tested states.

Verified: sample load; CSV upload; confirmed XLSX replacement; question entry; Shift+Enter newline; Enter/send; computed total 1000; actual North=400/South=600 chart; static inline chart preview; interactive panel; bounded result table; calculation view; PNG/HTML download; partial explanation retaining chart; safe provider failure; high-input notice and hover explanation; usage hover/click and recorded adjustment; clear chat keeping 3/14 used allowance; exhaustion disabling sends while retaining results; sidebar/mobile navigation; light/dark; session restart/expiry feedback; keyboard modal behavior.

Production flow had no browser console errors before deliberate expiry testing. The expected 401 during restart validation is not a JavaScript crash. Development hot reload during dependency/config edits produced transient dev-server messages; verification continued on the production build.

The intended Cloudflare CSP was also applied to production HTML through Playwright response interception. Chart rendering and both export downloads passed without console errors. The exported HTML was opened from a separate loopback static server: it rendered two bars and loaded zero external scripts. A missing favicon request from that temporary file server was incidental to the chart export. Final Shift+Tab from the modal's first control focused its last control, keeping focus inside.

Screenshots and synthetic download artifacts are under ignored `output/playwright/`. No private dataset or user conversation was saved there. The fixture is excluded from production packaging.

## Resource evidence and limits

Windows probes exercised the real loader and child calculation/chart process, sampling summed parent/child RSS every 20 ms:

| Case | Upload | Peak RSS | Result |
| --- | --- | --- | --- |
| 240,000-row CSV, API and all provider SDKs imported | 19.45 MiB | 384.28 MiB | Loaded and executed chart; load/import 3.69 s, worker 1.36 s |
| 200-column CSV, initial core-only probe | 19.07 MiB | 303.40 MiB | Loaded and executed chart |
| 20,000-row XLSX, initial core-only probe | 0.22 MiB | 216.89 MiB | Loaded and executed chart |

These are sampled Windows measurements, not Linux RSS guarantees or 0.1-CPU timings. Later probe versions import provider SDKs to avoid understating a warm API's footprint. Parsing can peak before DataFrame admission checks. Docker/WSL are absent, so container build/run and Render cold starts/resource behavior remain deployment acceptance checks. New live-provider integration has not been rerun; the existing verified provider logic is retained and new metadata parsing is tested offline.

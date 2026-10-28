# Dedicated web app verification

## Dataset-aware task menus — 2026-10-28

- Added offline regressions for value-free column facts (dates, booleans, identifiers, free text, empty/constant fields and missing counts) and API cache/lifecycle behavior. Full Python suite: **170 passed in 41.09 seconds**, with the existing Starlette/httpx deprecation warning. Column facts are computed once after upload admission, not on each snapshot/poll.
- Seven frontend tests pass, including four new suggestion cases: actual field references/date detection and sensible aggregates; deterministic ten-item limits with metric variety; all-text/date-only/numeric-only/no-date/empty schemas; quoted unusual names, oversized prompts and input immutability. The TypeScript/Vite production build passes; npm audit reports zero vulnerabilities.
- `scripts/verify_suggestion_ui.js` verifies against the network-blocked provider fixture on port 8001 and a separate frontend on 5174. Generate its synthetic CSVs first using `python scripts/browser_fixture.py --write-ui-fixtures`. See [setup](WEBAPP_SETUP.md) for the test environment. No production provider quota is used.
- Browser checks passed for hover, stationary gap traversal, entering/leaving menu items, pointer selection, arrow keys/Home/End/Enter/Escape, focus return to the prompt, and no automatic submissions. One deliberate selected chart request completed through the real loader/API/worker with provider doubles; choices remain available afterward and stay disabled during processing.
- Wide replacement data produced exactly ten options and the “Top 10” label, omitted IDs and stale previous-result choices, and allowed selection of the last item. Text-only replacement produced an honest no-date state; removal removed dataset menus. The test observed exactly one deliberate message request across all desktop browsing and selection actions.
- The inspected open desktop menu has zero axe violations. An initial scan caught the library's portal focus guards and out-of-landmark menu placement; fixed positioning within the existing main landmark preserves natural DOM order and avoids those hidden focus guards. Real touch events passed at 390/320px: menus fit the viewport without page overflow, selection focuses the editable prompt, and outside taps close the menu. Light/dark screenshots use synthetic data under ignored `output/playwright/`.
- Suggestions use bounded, deterministic rules, not semantic certainty or new model calls. Type/identifier/aggregation heuristics can require user correction. Basic execution checks remain **not a hardened security sandbox**. No commit, push or deployment.

## UX fixes — 2026-10-28

- Offline Python regression suite: **167 passed in 43.02 seconds**. The same upstream Starlette/httpx deprecation warning remains.
- `cd frontend; npm test`: three focused regressions cover dashboard sizing/title/axis preservation and input immutability, single/overlay-axis charts, and allowlisted preferences with malformed/unavailable storage. Node 24 runs these TypeScript helpers directly.
- TypeScript/Vite production build passes. Streamdown and chart rendering remain lazy: initial JavaScript is approximately 263 kB (83 kB gzip), answer rendering approximately 874 kB (269 kB gzip), plus on-demand diagram chunks; Plotly remains approximately 4.65 MB (1.42 MB gzip). The new Markdown/diagram capabilities add deferred assets rather than a new service or runtime budget.
- npm audit reports zero vulnerabilities. The math/diagram dependency tree uses the directly pinned KaTeX 0.19.1 through an npm override, avoiding older transitive KaTeX versions. Browser equation/diagram checks validate this combination locally.
- `scripts/verify_web_ui.js` is a Playwright CLI verification callback. It refuses to submit questions unless the verification-only server identifies itself via `/api/verification-fixture`. Run from the checkout with `scripts/browser_fixture.py` and Vite active, using `playwright-cli open http://127.0.0.1:5173` followed by `playwright-cli run-code --filename scripts/verify_web_ui.js`. Restart the fixture for a fresh message allowance when repeating checks.
- Checks exercise hover-gap traversal, opening usage details and leaving the control/card, full-width gutter scrolling, following content and respecting scroll breakaway, Latest message, reload anchoring after lazy chart loading, initial/reset autofocus, theme/sidebar retention, formatted tables/code/equations/diagrams, and a real four-panel Plotly dashboard with synthetic data. Delayed request acknowledgement and delayed completed-answer fetching verify that loading remains visible until content arrives.
- Mobile resize revealed that Plotly's root could collapse to zero height even while its SVG retained a height. An explicit root height fixes it; the browser check asserts visible height as well as figure geometry and horizontal scrolling. Multi-panel previews retain readable canvas dimensions and scroll sideways rather than compressing labels.
- PNG download produced a 1200×780 image. The downloaded HTML embeds Plotly, renders with no external script tags and retains dashboard height. A separate browser harness fed incomplete Markdown in eight-character chunks and verified final table/code/math/Mermaid output plus disabled raw HTML/images; diagram theme follows the application's light/dark selection.
- The inspected ready state has no axe violations after fixing the dataset button's accessible-name mismatch. Final production build, focused documentation links and diff whitespace passed. The synthetic fixture was then stopped and normal local API/UI startup verified with no provider inference calls.
- The API still polls complete answers; this verifies a streaming-ready renderer and resizing behavior, not live provider token streaming. Basic execution checks remain **not a hardened security sandbox**. No live providers, commits, pushes or deployment are part of these fixes.

## Original web implementation verification — 2026-10-27

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

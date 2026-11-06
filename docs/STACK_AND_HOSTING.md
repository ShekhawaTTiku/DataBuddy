# Selected stack and free-hosting target

Current status as of 2026-11-06. The public [ShekhawaTTiku/DataBuddy](https://github.com/ShekhawaTTiku/DataBuddy) release runs backend `d9854cd` on Render Free and frontend code including `ff4ae8c` on Cloudflare Pages. The public frontend is `https://databuddy-demo.pages.dev`. Hosted real-provider chat, calculations/charts, exports, Stop and progressive delivery/reload recovery passed. See [current deployment details](WEBAPP_SETUP.md#deployment), [verification](WEBAPP_VERIFICATION.md) and the [recovery checkpoint](PROGRESS.md). The dated selection and feasibility discussion below retains its original evidence and limits.

Date: 2026-10-26 (Asia/Kolkata). The owner asked the assistant to choose the stack and recommend the best free hosting for the agreed portfolio scope. The selection was subsequently implemented at the owner’s request; deployment remains separately authorized. See [working setup](WEBAPP_SETUP.md) and [verification](WEBAPP_VERIFICATION.md).

## Stack selected for implementation

| Layer | Selection | Reason |
| --- | --- | --- |
| Frontend | React + TypeScript, built with Vite | Supports the agreed interactive chat, panels, state and static frontend deployment. |
| Styling | Custom CSS with shared theme variables | Preserve the accepted design and allow palette/light-dark changes centrally. |
| Browser charts | Plotly.js through react-plotly.js | Reuse validated Plotly figure data from the Python core. Load charts on demand. |
| API | FastAPI on Python, served with Uvicorn | Wrap the existing UI-independent core rather than rewrite analysis behavior. |
| Analysis | Existing pandas, NumPy, openpyxl and Plotly Python | Preserve loader, calculation, evidence and chart behavior. |
| Providers | Existing Groq, Gemini and Mistral roles | Preserve verified primary/fallback and six-exchange memory behavior. |
| State | Bounded server-side session memory, frontend UI state | No database, accounts or saved conversation history. |
| Backend packaging | Docker image for deployment | A reproducible Linux runtime; Docker packaging is not a hardened execution sandbox. |
| Checks | Existing offline pytest plus relevant frontend/build/API/browser checks | Retain provider-free regression testing and verify real UI outcomes. |

Exact versions are pinned in `frontend/package-lock.json` and `requirements/api-lock.txt`. The frontend builds and the API/core regression suite passes.

## Hosting choice

**Preferred first deployment target: Cloudflare Pages Free for the static frontend, Render Free for the Python API. Render suitability remains conditional on resource tests.**

The frontend can show the interface while the API wakes up. API keys and provider requests remain exclusively on the backend. Using separate origins requires deliberate CORS/session handling; the implemented API uses a tab-scoped bearer token and explicit allowed origins.

Official documentation checked on this date:

- [Cloudflare Pages pricing](https://developers.cloudflare.com/pages/functions/pricing/): static asset requests are free and unlimited. This selection does not use Pages Functions for Python execution. [Free-plan limits](https://developers.cloudflare.com/pages/platform/limits/) still apply to builds, assets and project configuration.
- [Render compute plans](https://render.com/docs/compute-plans): Free provides **0.1 CPU and 512 MB RAM**. [Docker support](https://render.com/docs/docker) covers building from a Dockerfile or deploying an image.
- [Render Free limitations](https://render.com/docs/free): sleeps after 15 minutes without inbound traffic, usually takes about a minute to wake, has 750 shared workspace Free instance hours/month, and can restart. Service sleep/restart loses in-memory sessions. Include a clear waking-up/session-expired experience. Other free services in the same Render workspace share its hours.
- Render also limits bandwidth/build resources and may suspend services. Without a payment method, its documented behavior on bandwidth exhaustion is suspension rather than automatic supplementary billing. Do not select paid compute, enter paid trials or assume unlimited hosting/API use.
- [Hugging Face Spaces](https://huggingface.co/docs/hub/spaces-overview) currently requires a paid plan to create Docker compute Spaces, despite CPU Basic showing no hourly charge. It is therefore not selected as an unrestricted zero-budget Docker backend for a new free account. Its Gradio ZeroGPU exception does not directly match this FastAPI deployment design.

## Required feasibility check

An upload limit is not a memory-use limit: parsing, profiles, parent DataFrames, worker copies, provider SDKs and chart serialization share resources. A 20 MiB CSV/XLSX can exceed Render's 512 MB memory allowance, and 0.1 CPU can affect existing timeouts. Current Windows tests do not prove that this host fits.

Before confirming the backend deployment:

1. Measure Linux parent+worker peak memory and calculation times with synthetic datasets, the ordinary demo, representative permitted near-limit uploads and chart requests. Verify bounded admission/concurrency and session expiry rather than assuming many simultaneous datasets fit.
2. Exercise real subprocess execution in the deployment-like environment, with appropriate worker timeout behavior and cleanup. Keep normal tests offline.
3. Keep the agreed 20 MiB upload ceiling unless the owner explicitly changes it; resource checks may reject otherwise excessive datasets with a clear explanation. If the intended workload cannot fit, revisit hosting or scope rather than silently reduce the agreed cap or activate a paid plan.
4. Verify upload/proxy limits, frontend/API session behavior, origins, secrets, cold starts and resource-failure feedback before publishing.

Basic execution safeguards remain intended for trusted demonstrations and are not a hardened security sandbox. Neither Render nor Docker packaging changes that claim.

## Next stage and publication boundaries

Updated 2026-10-30: the existing production image builds/runs on Linux amd64, all 183 Linux tests pass, and eight local 512 MiB/no-swap probes pass at 1 CPU and 0.1 CPU. Production HTTP startup/restart checks pass under the strict cap. See [container verification](CONTAINER_VERIFICATION.md). These measurements support trying Render Free; they do not establish actual hosted cold-wake/proxy/provider behavior or certify every allowed dataset/session combination. Create hosting accounts/services and deploy only when explicitly authorized.

The earlier Sites publication request was cancelled as accidental. It caused no Site creation, publication or file changes. Sites is not this application's selected hosting platform. No commit, push or deployment is part of this stack-selection task.

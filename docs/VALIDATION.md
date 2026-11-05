# Validation record

## README publication checks — 2026-11-05

Fresh verification before publishing the updated public-repository and profile READMEs passed **183 offline Python tests in 45.07 seconds**, ten frontend tests and the TypeScript/Vite production build. The known upstream Starlette/httpx deprecation warning remains. Both READMEs passed GitHub Markdown rendering, local document-link checks and current-demo-link checks. The application README preserves the attached reference's section order. Candidate documents passed checks for configured provider-key values. These checks used no live provider inference.

## Local Linux container acceptance — 2026-10-30

Fresh Windows suite: **183 tests in 44.83 seconds**; Linux suite: **183 tests in 25.68 seconds**, with the known Starlette/httpx warning. Ten frontend tests and the production build pass. The unchanged production Dockerfile builds on Linux amd64 with all 47 locked packages and passes non-root/private-file checks. Eight 512 MiB/no-swap synthetic probes pass at 1 CPU and 0.1 CPU; strict workers complete within 30 seconds with no OOM events. Production HTTP startup/restart checks also pass under the strict limits. No provider quota or deployment was used. See [container verification](CONTAINER_VERIFICATION.md) for the exact test environments, measurements, reproduction and remaining hosted limitations.

## Private GitHub update preflight — 2026-10-27

The owner authorized grouped publication of the existing dedicated-app changes. Fresh checks: **167 Python tests passed in 33.51 seconds**, with one documented upstream Starlette TestClient/httpx deprecation warning; `python -m pip check` passed; `npm run build` passed TypeScript/Vite production compilation; npm audit reported zero vulnerabilities. No live provider calls, deployment or new browser/resource acceptance run was performed during this publication. The existing dedicated-app browser/resource evidence below remains dated. Publication safety and commit groups are recorded in [GITHUB_CHECKPOINT.md](GITHUB_CHECKPOINT.md).

Current dedicated-app checks are in [web app verification](WEBAPP_VERIFICATION.md). Historical results below remain dated evidence.

## Authorized private GitHub checkpoint — 2026-10-22

The owner subsequently authorized grouped commits and separate pushes to the new private DataBuddynew repository. Fresh pre-publication validation passed **152 tests in 31.69 seconds**, with no live model calls and no broken dependencies. Current files, staged batches and the existing 44-blob history were checked for credentials/private-data paths. Destination, commit batches, local-only exclusions and recovery guidance are recorded in [GITHUB_CHECKPOINT.md](GITHUB_CHECKPOINT.md). Earlier statements that changes were uncommitted or unpushed describe the earlier stages and are not the current publication status.

## Final live Superstore verification — 2026-10-22

The owner supplied the Superstore CSV and authorized completion of live verification. **Twelve real exchanges passed**, including exact calculation/chart evidence, both memory rollovers and recall of an early preference. Actual browser upload/chart rendering, PNG/HTML download, reset/removal and corrected reupload notices passed. Final fallback code/chart/narration/memory passed with working Ministral 14B; Mistral Medium had zero requests/minute allowance and is no longer the default. Native Gemini compression passed separately. Full evidence, timings, provider operations, diagnostic attempts and limitations are in [LIVE_VERIFICATION.md](LIVE_VERIFICATION.md).

**Final offline suite: 152 passed in 32.05 seconds.** New regressions cover Gemini's minimum deadline, available fallback time, one-call rollover and product dimensions not producing date warnings. Dependency consistency and direct pin checks passed. The saved .env and supplied CSV match original backup hashes; no private values are recorded. Live checks were separately opt-in and consumed API quota; pytest remains offline. Existing earlier statements that no live calls had been made apply to their historical stages only.

Final post-documentation checks: 27 Python files parsed; all local README/docs links resolved; whitespace and exact configured-key scans passed. All four completed live acceptance/native-compression/fallback reports show passing outcomes. Original checkout remains clean at `8d3b78a`; working HEAD remains `11c1a1a` on `codex/demo-stability-fixes`. The temporary browser tab/server were closed. No commits or pushes.

## Latest stage: Gemini memory and Mistral role fallback, 2026-10-22

The historical 2026-10-21 results below remain baseline evidence. This stage implements the owner-approved provider/memory behavior documented in [PROVIDERS_AND_MEMORY.md](PROVIDERS_AND_MEMORY.md).

- Final full offline suite: **146 passed in 30.81 seconds**. The initial stage rerun passed 145 tests in 30.53 seconds before the extra real-SDK transport regression was added.
- Focused final provider/memory/Streamlit/CLI checks: 52 passed in 6.34 seconds, including the additional installed Gemini SDK request-serialization test through fake HTTP transport.
- New coverage: six/twelve-exchange rollover, merging the previous paragraph, length bounds, blank responses, repeated outages, failed-compression retry, actual Google APIError classification, role-specific Mistral fallback, configuration errors, shared deadlines and fallback time reservation, evidence separation, reset/replacement/session isolation, answer preservation, safe UI/CLI notices and reruns without extra memory calls.
- `python -m pip check`: no broken requirements. All 26 current Python/test files parsed. `git diff --check`: passed with Windows line-ending notices only. README/docs local links resolved; exact configured-key scan found no private-key values in tracked/new non-ignored project files.
- Dependency snapshot: 10 direct runtime packages, 63 installed runtime packages including Google Gen AI 2.25.0. No installation/upgrade or clean-install test was performed.
- Original backup: read-only Git checks confirm revision `8d3b78a`, no tracked differences/non-ignored untracked files and 133 files present. A byte-for-byte comparison to the old aggregate could not be reproduced from its serialization description; ignored backup content is not newly certified by this stage. No backup edits were made.
- Working HEAD remains `11c1a1a`, branch `codex/demo-stability-fixes`. Changes remain uncommitted. No pushes, deployment or replacement frontend.
- All provider tests are offline, using fake clients or in-memory HTTP responses. No live inference, account quota/access check or live summary-quality evaluation was performed. Existing browser visual/PNG, clean-install, Linux and hardened-isolation limitations still apply.

Date: 2026-10-21 (Asia/Kolkata). Working checkout: D:/projects/databuddy 2.0. Verified environment: Windows, Python 3.11.9; direct and transitive runtime versions are recorded in the requirements files.

## Results

| Check | Result |
| --- | --- |
| Full offline regression suite | **116 passed in 29.38 seconds** |
| Loader tests | 22 passed: memory/path/stream sources, CSV/XLSX, size/shape/empty/malformed input, leading-zero values, safe dates and bounded profiles |
| Runner tests | 36 passed: real calculations/charts, print/import protocol, timeout, output limits, basic I/O rejection, environment and cleanup |
| Analysis/conversation tests | 22 passed: routing, follow-ups, bounded context, session isolation, reset and preserved partial success |
| Provider/session helper tests | 20 passed: safe errors, quotas/authentication, retries/budgets, SDK options, transactional upload and history limits |
| Streamlit UI tests | 6 passed: real file upload/replacement, rejected-file recovery, reset/removal, escaped filename, missing configuration, displayed computation and lazy export |
| Documented synthetic-demo tests | 8 passed: totals, averages, grouping, monthly results, missing values and no restored state |
| Terminal tests | 2 passed: preserved evidence and session reset without model calls |
| Installed dependency consistency | python -m pip check: no broken requirements |
| Syntax | 25 current Python/test files parsed successfully |
| Git diff whitespace check | Passed; ordinary Windows line-ending notices only |
| Current documentation links | All local links in README/current docs resolved |
| Credential hygiene | No exact matches for configured private API keys in tracked/new non-ignored files or existing Git history; no key values displayed |
| Ignore rules | .env, .streamlit/secrets.toml, uploads and .databuddy_state ignored |
| Original backup | All 133 files match the pre-work aggregate SHA-256; no backup changes |
| Git activity | HEAD remains upstream 11c1a1a on local fixes branch; changes uncommitted, no pushes or deployment |

## Additional checks

The private local Superstore CSV loaded as 9,994 rows by 21 columns. Deterministic Sales total was 2,297,200.86; Profit total was 286,397.02. Only aggregate validation results are recorded here; private rows are not included. A separate offline UI review prepared an HTML chart download successfully and confirmed the plotted-data/internet disclosure.

Independent integration review checked upload state, UI error branches, CLI partial success, SDK signatures, worker policy/environment and documentation truthfulness. Found issues were corrected and covered by tests. Prompt instructions were aligned with the final no-query/eval/to_string execution policy and analysis tests were rerun afterward.

## Limits of this verification

- No live provider inference calls were made and no API quota was intentionally consumed. Actual account authentication, model availability, rate limits and generated-answer quality still require an owner-run demonstration with available free quota.
- Streamlit behavior was exercised headlessly with its first-party AppTest, including real uploaded-file widget interactions. Actual browser PNG download/mobile appearance was not visually tested. No local server was left running.
- Existing installed dependencies were tested and recorded. A clean-environment install, Linux host, production deployment and dependency-vulnerability audit were not performed.
- Passing tests do not establish hardened isolation. The trusted-demo worker has no OS-enforced memory/network sandbox and must not be exposed as arbitrary public code execution.
- No database, account system, saved dataset/history, new HTTP API or replacement frontend was added. Browser close is not an immediate memory-deletion guarantee; uploads are not durably saved by the app.

## Reproduce

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pip check
```

See DEMO_CHECKLIST.md for the small synthetic CSV and known expected answers. Keep this record and WORK_LOG.md current after subsequent changes.

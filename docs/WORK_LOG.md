# DataBuddy readiness work log

## Plain-language change history — 2026-10-25

- The owner requested a document containing the explained change list and explicitly authorized a terminal commit/push using the configured Git identity to the new DataBuddy repository.
- Added `CHANGES_EXPLAINED.md` with the original starting point, 29 grouped changes, simple reasons, historical verification evidence, and material limits. Linked it from the documentation index. Scope is the implementation recorded through 2026-10-22; application behavior is unchanged.
- Publication is limited to these three documentation files in the working checkout. The original backup, credentials, datasets, and saved conversations are excluded. Basic execution protections remain explicitly described as not a hardened security sandbox.
- Validation for this documentation update: local Markdown file links, all 29 change sections, the execution limitation, and diff/whitespace checks passed. The offline suite passed **152 tests in 33.23 seconds** without live provider calls. A fetch confirmed the starting local/remote commits matched. The terminal push targets `origin/main` without force; remote commit identity and final working status are checked afterward. Any publication failure is reported in the accompanying task result.

## Private GitHub publication — 2026-10-22

- The owner confirmed publication to `ShekhawaTTiku/DataBuddynew`, requested grouped pushes and reiterated that credentials/private datasets must remain local. Verified destination privacy and empty branch state before publishing.
- Scanned 71 current candidate files and 44 historical blobs for configured keys, recognizable credential formats, private datasets and saved state. Only the synthetic example CSV is eligible for versioning. Preserved existing audited history rather than rewriting it.
- Renamed the working copy's old `origin` to `upstream` and configured the new private repository as `origin`. No remote settings or files in the original backup were edited.
- Fresh offline preflight: 152 tests passed in 31.69 seconds; dependencies passed. Staged only explicit file groups, checked every batch before committing and verified remote `main` after each push.
- Published batches 1–4 for core safeguards, providers/memory, interfaces and tests/demo tools. Batch 5 contains documentation and aggregate-only verification evidence, including GITHUB_CHECKPOINT.md. Each batch uses a separate commit and push; no force pushes, tags or deployment.
- The final checkpoint verification checks remote/local identities, repository privacy/file inventory, local worktree/index, private ignore rules and original-backup status. The checkpoint guide records the scope and recovery reference; older no-commit/no-push entries below describe the earlier, pre-authorization stages.

Latest stage: owner-authorized private GitHub checkpoint on 2026-10-22. See [GITHUB_CHECKPOINT.md](GITHUB_CHECKPOINT.md) for publication batches and exclusions, and [LIVE_VERIFICATION.md](LIVE_VERIFICATION.md) for application outcomes. Earlier entries below remain historical; their no-commit/no-push statements describe the earlier stages, before publication was authorized.

Date: 2026-10-21 (Asia/Kolkata). Work takes place only in `D:/projects/databuddy 2.0`.

## Scope and constraints

Personal showcase with trusted demonstration data, up to 20 MiB per file. No database, persisted conversations, accounts, paid infrastructure, new frontend, deployment, commits, or pushes. Keep the existing Streamlit and terminal entry points working. Basic execution protections are not a hardened security sandbox.

## Baseline

- Original `D:/projects/DataBuddy` is the untouched local backup.
- Refreshed remote tracking and fast-forwarded the working copy from `8d3b78a` to `11c1a1a`; both incoming changes affect README only.
- Created local branch `codex/demo-stability-fixes`. No new commits or pushes.
- Backup snapshot: 133 files; SHA-256 aggregate `55a09aa1c5084711b158fa15e96f65627ecd496d6e45af1f5b10d29c6674a428`.
- Reviewed source files and Streamlit's version-matched session-state/testing guidance.

## Completed implementation steps

1. Reviewed the two local copies, confirmed the newer working baseline and preserved the original backup. Refreshed only the working checkout from GitHub; no new commits or pushes.
2. Added bounded memory-only CSV/XLSX ingestion, content fingerprints, transactional replacement, import notices, leading-zero preservation and conservative dates. Verified the existing Superstore CSV and synthetic fixtures.
3. Reworked the existing runner's result channel and permitted imports. Added shared basic code rules, minimal child environment, isolated temporary working directory, hard timeout and bounded pipes/results/charts. Parent accepts validated JSON, not worker pickle.
4. Derived chart evidence from actual plotted values. Saved successful chart/computation before optional narration. Bounded session memory/prompt assembly and removed active Gemini summary code/settings/dependency/prompt.
5. Moved Streamlit secret bootstrap out of core configuration. Allowlisted secret settings, added safe provider errors, disabled duplicate SDK retry layers and bounded provider time/token/context usage. Default visualization suggestions are off to save calls.
6. Kept the existing Streamlit design while fixing upload, display, reset and removal controls. Escaped dynamic HTML, exposed evidence, disabled unconfigured input, replaced repeated server PNG work with browser export and on-demand HTML.
7. Pinned nine direct runtime packages and recorded the tested Windows transitive runtime snapshot (55 packages). Removed unused Google GenAI/Kaleido dependencies. No packages were installed/upgraded.
8. Replaced the duplicated README and outdated current guides, retained clearly labeled historical references in docs/history, and wrote setup, scope, architecture, privacy, demo and validation guides. Added project guidance to keep docs maintained.
9. Added offline provider, loader, runner, conversation, analysis, UI, CLI and documented-demo regression tests. Tests use fake provider responses and block external network connections in the parent process; Windows asyncio loopback is allowed.
10. Independent integration review found and corrected Unicode encoding in interface text, repeated rejected-file parsing and hidden CLI evidence. A second safety review found an aliased to_string file-output path; generated calls to that method are now rejected, with regression tests.
11. Final combined tests, dependency consistency, syntax, documentation links, known-key scan, ignore rules, Git status and backup identity were rechecked. Actual outcomes are recorded in VALIDATION.md.

## Implementation choices worth retaining

- Uploads remain in memory; no fragile browser-close cleanup mechanism was added. Temporary worker transport files are cleaned after calculation, including handled failures/timeouts.
- Preserve ambiguous dates and show import notes instead of silently coercing values to missing data.
- Keep the last successful calculation/chart when optional model narration fails. Do not narrate failed execution as a successful answer.
- XLSX remains supported for its first sheet; unsupported Excel variants were removed from advertised formats.
- Basic safeguards are intentionally understandable; no OS sandbox, database, account system, queue, new API or replacement frontend was introduced.

## Independent review handoff

- Added `ANTIGRAVITY_REVIEW_HANDOFF.md` after the owner requested a detailed checklist for a second opinion. It records all 18 implemented work packages, prior validation evidence, unchecked independent verification steps, current limits, excluded work, optional checks and future stages in order.
- The handoff asks Antigravity to challenge the code, tests and documentation, distinguish reproduced issues from speculation, and prioritize simple zero-budget improvements. It requests review/reporting rather than application edits, live model calls, commits, pushes, deployment or a new frontend.
- Added the handoff to the documentation index and guarded the setup example so it does not overwrite an existing `.env`.
- This handoff task changes Markdown documentation only. The earlier 116-test result remains historical implementation evidence, not a claim that a fresh full suite was run for a documentation-only change. Local links and checklist structure were checked.

## Documentation policy

Record what changed, why, how it was checked and remaining limitations. Never include API keys, private CSV contents, saved conversation contents or full provider errors. Update this log when a stage completes; user-facing instructions belong in README and the focused guides under this directory.

## Owner-approved provider and memory implementation — 2026-10-22

- Authorization: the owner chose a brief note per completed exchange, six notes compressed into one rolling paragraph, the next six merged into its replacement, and Mistral fallback for all Groq/Gemini tasks. The role table was discussed and explicitly approved before implementation. No new frontend, API, persistence, database, commit, push or deployment was requested or added.
- Corrected an earlier explanation: the original backup already discarded older turns without summarizing them. Its Gemini function/settings were unused; the initial readiness cleanup removed unused plumbing, not active summarization. The new cycle is an added working feature.
- Preserved the Mistral SDK import fallback. Independently checked installed SDK 2.10.1 and official docs: `mistralai.client.Mistral` is valid and needed in this environment. Added a maintainer note to the earlier Antigravity report rather than silently adopting finding F1 or rewriting its conclusions.
- Added environment/Streamlit secret settings for Gemini and `MEMORY_MODEL` (default `gemini-3.5-flash-lite`). Retained Groq GPT-OSS 120B, Ministral 8B routing/chat, Ministral 14B explanations, and Mistral Medium code fallback. Split Groq code and narration roles so narration falls back to Ministral 14B. Gemini note/compression requests also fall back to Ministral 14B. Existing private `.env` and secrets were not edited; no existing model overrides were found there.
- Added Google Gen AI using the already-installed version 2.25.0 and regenerated the installed Windows runtime dependency snapshot (10 direct/63 runtime packages). No packages were installed/upgraded. Confirmed request options and retry behavior against installed SDK and official references. Tested actual installed SDK serialization using an in-memory fake HTTP response.
- Implemented one note per completed exchange, six-note rollover, one replacement paragraph, 400-character notes, 2,000-character paragraph, 768-token memory responses and six recent full exchanges by default. The old paragraph is replaced only after successful compression. Conversation summaries remain untrusted context and are excluded from code-generation analysis context; separate actual computed evidence remains authoritative.
- Centralized completed-exchange recording in `DataBuddy.ask` so exchanges are recorded once, including partial explanations and clarification branches. Successful calculations/charts are preserved before optional narration and memory. Safe memory notices appear in UI/CLI and persist through normal Streamlit reruns without triggering new summary calls.
- On memory failure, retain the previous paragraph and bounded recent history/notes; local clipped notes are explicitly marked uncompressed. Failed compression retains six notes and is retried after a later successful note. Repeated outages may drop older uncompressed details, which is documented rather than claiming unlimited recall.
- Extended nested request budgets: memory has a 10-second default cap for note+compression combined within the existing question deadline. Primary Groq/Gemini calls reserve part of the remaining time for Mistral. SDK retry layers stay disabled. Temporary failures/quota limits permit fallback; permanent key/model/access errors produce safe configuration messages. Routing still uses local rules for outages/malformed output while surfacing permanent configuration failures.
- Updated README, setup, architecture, privacy, implementation plan, demo checklist and documentation index. Added `PROVIDERS_AND_MEMORY.md` with model references, lifecycle, bounds, failure behavior and a review checklist. Marked earlier Antigravity no-summary checks as superseded and preserved its original report with a clearly attributed maintainer addendum.
- Verification: focused provider/memory/analysis tests passed; the final full suite passed **146 tests in 30.81 seconds**, including the real-SDK transport regression. Full outcomes are recorded in `VALIDATION.md`. Dependency consistency, Python parsing, local documentation links, exact configured-key scan and whitespace checks passed. No live inference or API quota was used.
- Backup check: the original checkout remains at `8d3b78a`, with no tracked diff or non-ignored untracked changes and 133 files. The earlier aggregate hash was not reproduced using the available description of its serialization, so this stage does not claim a fresh byte-for-byte validation of ignored backup data. All edits and tests targeted the working `databuddy 2.0` checkout.
- Remaining verification: actual provider account access, live summary fidelity/free quotas, clean installation and browser visual QA were not exercised. Summaries can forget or misstate details. Closing a browser is still not an immediate server-memory cleanup guarantee. No paid account setting or service was activated.

## Antigravity independent review completion

- Date: 2026-10-21 (Asia/Kolkata).
- Role: Antigravity second-opinion review per `ANTIGRAVITY_REVIEW_HANDOFF.md`. Conducted strictly in review-only mode.
- Verification: Full offline regression suite re-run independently: 116 passed in 29.23s. Git status, backup safety, AST execution policy, synthetic demo calculations (`examples/demo_sales.csv`), and secret protection were verified independently.
- Findings: Six minor findings identified (F1 dead `mistralai` import fallback, F2 `uploads/` folder clarity, F3 blocked `to_string` tradeoff, F4 legacy `.databuddy_state` files, F5 minor test assertion gap in `write_chart_insight`, F6 untested `explain_analysis` without prior analysis).
- Recommendation: Proceed with documented limitations. Two small pre-demo fixes proposed (F1, F2). No application code modified, no API quota consumed, no commits or pushes created. Full report recorded in `docs/ANTIGRAVITY_REVIEW.md`.

## Owner-authorized live Superstore verification — 2026-10-22

- The owner supplied `uploads/Superstore.csv` and requested completion of verification. Used real configured provider calls and the actual Streamlit browser; kept normal tests offline. No paid plan/account changes, commits, pushes, deployment or replacement frontend.
- Independently calculated expected aggregates from 9,994 rows / 21 columns and compared generated execution/chart evidence. Kept only aggregate checks and safe provider metadata in reports; no source rows, full responses, credentials or conversation text were saved.
- Verified provider catalogs, then actual inference. Catalog listing proved insufficient: Mistral Medium returned HTTP 429 and a zero request/minute limit. Tested Ministral 14B code/chart generation successfully and changed the default `MISTRAL_FALLBACK_MODEL`/example to that working zero-budget alternative. Environment overrides remain supported; private .env unchanged. Final full fallback pipeline, narration and memory passed.
- Live tests exposed Gemini's minimum ten-second API deadline, which the old six-second primary slice violated. Set default memory budget to 20 seconds; reserve a valid Gemini slice when it fits, otherwise skip to Mistral without exceeding shared deadlines. Disabled unneeded automatic function calling and used minimal thinking for compatible Flash-Lite models.
- First rollover retry showed two sequential memory calls could exhaust the sub-budget. Combined sixth-exchange briefing and paragraph merging in one request, preserving the six-exchange behavior with fewer calls. Updated regressions and docs. Preserved the two stopped diagnostic attempts separately from the successful final run.
- Fixed a misleading product-dimension/date notice discovered on Superstore. A synthetic `3-1/2 inch` fixture verifies that product text is not treated as a date while existing ambiguous/mixed date preservation tests still pass.
- Completed twelve real exchanges: calculations, explanation, chart, chart title change, six-note rollover, new notes, old-preference recall and second rollover. All passed with no memory notice. Gemini completed six of twelve memory operations directly; bounded timeouts exercised successful Mistral fallback for the others, including both rollovers. Separately confirmed native Gemini paragraph compression with synthetic aggregate notes.
- Verified actual browser upload, chart values/narration, PNG and HTML downloads, CDN/plotted-data disclosure, reset/removal and fresh corrected upload. Saved aggregate-only PNG/screenshot evidence under docs/verification. Cleaned up temporary browser/server after checks.
- Final offline suite: **152 passed in 32.05 seconds**. Dependency consistency/direct pins passed. Saved private .env and CSV hashes match original counterparts. Full results and unverified areas are documented in LIVE_VERIFICATION.md and VALIDATION.md. HEAD remains unchanged and all project fixes remain local/uncommitted.

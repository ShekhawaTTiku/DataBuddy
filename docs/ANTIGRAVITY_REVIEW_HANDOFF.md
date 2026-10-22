# DataBuddy: independent review handoff and complete readiness checklist

> Update 2026-10-22: the owner subsequently approved and requested active Gemini six-note/rolling-paragraph memory with Mistral fallback for all Groq/Gemini tasks. The original checklist below describes the earlier readiness baseline; its no-Gemini/no-summary checks are superseded by [PROVIDERS_AND_MEMORY.md](PROVIDERS_AND_MEMORY.md). Review the new memory verification checklist and current [VALIDATION.md](VALIDATION.md) as well. Keep the Mistral SDK import compatibility fallback; it is needed by installed SDK 2.10.1. Review remains offline and review-only.

Prepared on **2026-10-21**, using the owner's Asia/Kolkata date context.

**Audience:** Antigravity or another independent reviewer with local access to this repository.

**Purpose:** independently check the existing application, challenge the previous implementation and validation, identify remaining practical problems, and give the owner a second opinion before designing a replacement frontend.

This is a review brief, not an instruction to rebuild the application. A checkbox is intentionally unchecked until the independent reviewer supplies evidence. Previous reported passes are a starting point, not proof that this review has passed.

---

## 1. Start here: the request to Antigravity

Please review this project as an independent engineer. Do not simply repeat the previous assistant's conclusions. Read the actual working files, inspect the uncommitted changes and newly added files, run the appropriate offline checks, and compare behavior with the documentation.

The owner wants a reliable personal portfolio demonstration, not an enterprise SaaS product. Prioritize correct answers, reliable uploads, usable charts, straightforward failure recovery, simple safeguards, clear documentation and zero unnecessary costs.

Please answer these questions explicitly:

1. Does the current app actually do what its README and guides say?
2. Did the readiness fixes introduce regressions, excessive restrictions, unnecessary complexity or unsupported assumptions?
3. Which problems can you reproduce, and which are only hypotheses?
4. Do the tests check real outcomes, or do mocks hide important failures?
5. What is the smallest sensible set of additional changes, if any, before a recruiter/friend demonstration?
6. Which changes can wait until the future dedicated web app is designed?
7. Is anything described as completed actually incomplete or only partially verified?
8. What would you simplify, remove or defer for this personal-project scope?
9. What are your five most useful suggestions, with expected benefit, effort, cost and tradeoffs?
10. Would you proceed to design, proceed with stated limitations, or fix specific issues first? Explain using evidence.

Start in **review-only mode**. Do not modify application code, reformat the repository, install/upgrade packages, consume model quota, create commits, push, merge, deploy or build a new frontend as part of this review. Report proposed changes first. You may write the review report to `docs/ANTIGRAVITY_REVIEW.md`; do not overwrite an existing report without preserving it or asking the owner. Updating that report is the only file-writing activity requested by this handoff.

If only this Markdown file is available, you can review the plan but cannot verify the implementation. Mark source-dependent checks `NOT VERIFIED` and request access to the working folder. Do not invent a passing result.

## 2. Non-negotiable scope and permissions

| Topic | Owner's decision |
| --- | --- |
| Intended audience | Owner, friends and recruiters; very low usage |
| Data | Trusted, ordinary, non-sensitive demonstration CSVs |
| Main input format | CSV; existing XLSX support is retained for its first sheet |
| Maximum file size | 20 MiB = 20,971,520 bytes, shown in the interface as 20 MB |
| Persistence | Current run/session only; no database or saved conversation/dataset service |
| Operating budget | Zero; no paid infrastructure or automatic paid upgrades |
| Current interface | Keep the existing Streamlit and terminal interfaces functional |
| Current task | Stabilize and independently review the existing app; prepare its core for a later frontend |
| New frontend/API | Not authorized during this review |
| Git changes | Do not commit, push, reset, clean, merge, rebase or force-update anything |
| Original backup | Never edit or delete `D:/projects/DataBuddy` |
| Private files | Never print, upload, paste into a report or send to another service |
| Live model calls | Not part of default review; require a separate owner decision because they consume quota and disclose prompt content |

Do not assume a publicly reachable URL is safe merely because the intended audience is small. If hosting is discussed later, distinguish controlled demonstrations from unrestricted anonymous uploads and code execution. Report this distinction without automatically expanding the project into an enterprise platform.

The earlier research produced a broader 60-point product backlog. The owner deliberately reduced that scope. The 18 work packages in this handoff are the agreed implementation scope; the entire research backlog is not a mandatory prerequisite for this personal demonstration.

## 3. Folders, Git state and recovery context

### Active working copy

`D:/projects/databuddy 2.0`

All implementation changes and the current `docs` folder are here. Review this folder, not the old backup.

### Original local backup

`D:/projects/DataBuddy`

The owner chose an ordinary local folder backup because that was easier to understand than Git recovery. It was preserved unchanged while work happened in `databuddy 2.0`.

### Earlier folder preserved separately

`D:/projects/databuddy 2.0.previous`

This contains the older terminal-only project that occupied `databuddy 2.0` before replacement. Deleting its contents was blocked by automatic approval review, so it was renamed and preserved. It is not the current working app and is not the primary backup of the newer version. Do not delete it as part of review.

### Git baseline

- Remote: `https://github.com/ShekhawaTTiku/DataBuddy.git`.
- The newer local project initially pointed to `8d3b78ac5048af99ac765403495d09e622abb872`.
- The working copy was fast-forwarded to `11c1a1a38d0e8d6115008b93bb26e07957f8e38f`.
- The two incoming commits were `dccdcf3` and `11c1a1a`, both README-only changes.
- Local working branch: `codex/demo-stability-fixes`.
- **The readiness fixes are uncommitted.** HEAD identifies the upstream baseline, not the completed fixes.
- No new commits, pushes or deployment were performed during the readiness work.
- Do not treat `git show HEAD` as the current implementation. Inspect working-tree changes **and untracked files**. `git diff` alone omits newly added, untracked files.

### Previous backup verification

The original backup had 133 files. A previous aggregate SHA-256 check matched before and after implementation:

`55a09aa1c5084711b158fa15e96f65627ecd496d6e45af1f5b10d29c6674a428`

That digest was calculated by sorting all files under `D:/projects/DataBuddy`, feeding each relative POSIX-style path and the SHA-256 bytes of its content into one aggregate SHA-256. It includes hidden/Git files. A later external change to any included file can change the digest; investigate before attributing a difference to application code. Do not run mutating Git commands against the backup.

## 4. Documents to read, in order

1. Repository `AGENTS.md`: local working rules and the documentation requirement.
2. Repository `README.md`: current public description and quick start.
3. [Implementation plan](IMPLEMENTATION_PLAN.md): the 18 agreed work packages.
4. [Work log](WORK_LOG.md): steps actually taken, decisions and review corrections.
5. [Architecture](ARCHITECTURE.md): modules and request/data flow.
6. [Setup](SETUP.md): configuration, dependency snapshot and commands.
7. [Security and privacy](SECURITY_AND_PRIVACY.md): protections and remaining limits.
8. [Demo checklist](DEMO_CHECKLIST.md): synthetic data and expected answers.
9. [Previous validation record](VALIDATION.md): reported checks and explicit gaps.
10. Source code and tests: the final authority when documentation and behavior disagree.

The root `DataBuddy_Project.md` and `PROJECT_DOCUMENTATION.md` are pointers. Their old contents are retained under `docs/history/` with warnings. Historical statements about persistence, summarization, privacy and safety are not current claims.

## 5. What was implemented: complete work-package inventory

Every entry below means **implemented according to the previous work record; independently verify it**.

| # | Change and purpose | Main evidence to inspect |
| --- | --- | --- |
| 1 | Synchronized the working baseline with upstream README updates; kept the original folder as backup | Git state, work log, original-backup identity |
| 2 | Enforced a 20 MiB upload cap in UI and Python; CSV primary, XLSX retained, unsupported Excel variants removed | `.streamlit/config.toml`, `config.py`, loader, file uploader |
| 3 | Detect same-name changed content and replace dataset only after success | `ui_state.py`, `web_app.py`, replacement tests |
| 4 | Clear errors for empty, malformed, oversized and unsupported files; avoid reprocessing rejected uploads on every rerun | Loader errors, rejected fingerprint/error state, UI tests |
| 5 | Prevent silent date-coercion losses; preserve leading-zero CSV identifiers | `dataset_profiler.py`, date and identifier tests |
| 6 | Fix print/JSON interference and inconsistent permitted imports | `_runner.py`, `executor.py`, `execution_policy.py`, runner tests |
| 7 | Add simple code rules, restricted builtins, minimal worker environment, temporary cwd, timeout and cleanup | Runner/policy implementation and tests; honest security docs |
| 8 | Bound question/context/profile/code/results/chart/pipe sizes | `config.py`, prompt assembly, runner formatting and bounds tests |
| 9 | Ground chart commentary in actual computed/plotted evidence | `_chart_evidence`, `write_chart_insight`, chart prompt and tests |
| 10 | Preserve successful computation/charts when optional narration fails | `databuddy.py`, partial-success tests, CLI/UI evidence display |
| 11 | Keep bounded in-memory conversation/chart state only; remove active Gemini summaries | `conversation_state.py`, removed code/settings/dependency/prompt |
| 12 | Make reset/removal controls clear; keep uploads in memory and remove worker files | `ui_state.py`, memory loader, runner cleanup tests |
| 13 | Add safe provider errors, explicit SDK timeouts/token caps, shared request budget, bounded retries and fallback | `llm_clients.py`, fake-client tests, config |
| 14 | Escape dynamic HTML and use native table/text rendering for data details | Filename/suggestion rendering, UI tests |
| 15 | Remove repeated server PNG rendering; browser PNG and on-request HTML export | `_render_chart`, removed Kaleido dependency, export tests |
| 16 | Improve loading/configuration feedback, active dataset display and evidence inspection without redesign | Existing Streamlit interface and AppTest cases |
| 17 | Separate UI-specific secret loading from core; protect secrets and pin tested dependencies | `streamlit_support.py`, `config.py`, ignore/example/requirements files |
| 18 | Add focused offline regression tests, synthetic demo and maintained documentation | `tests/`, `examples/demo_sales.csv`, `docs/` |

### Additional corrections made during implementation review

- Corrected Unicode/emoji text encoding in the existing interface.
- Stopped an invalid selected upload being parsed again on each rerun.
- Made the terminal display preserved computed evidence when narration fails.
- Blocked generated `to_string` calls after discovering file-output paths through aliases or expanded keyword arguments.
- Aligned generation prompts with the final boolean-mask/no-query/no-eval/no-to_string rules.
- Kept successful charts in session memory before attempting narration.
- Removed the unused summarization prompt and Google GenAI dependency.
- Replaced duplicated README content and labeled historical documentation.
- Added a small synthetic demo instead of committing the owner's private uploaded CSV.

## 6. Source-code map for the reviewer

| File/directory | What it does | Review emphasis |
| --- | --- | --- |
| `web_app.py` | Existing Streamlit interface | Correct active dataset, errors, reset, safe display, downloads |
| `app.py` | Terminal interface | Commands, readable errors, evidence on partial success |
| `streamlit_support.py` | Streamlit Secrets bootstrap | Runs before core imports; allowlisted values only |
| `config.py` | Environment-backed validated limits/settings | No Streamlit import; no active Gemini summary settings |
| `ui_state.py` | UI-independent session helpers | Content fingerprint, atomic replacement, bounded display state |
| `dataset_state.py` | Compatibility/export interface | Supported extensions and loader contract |
| `dataset_profiler.py` | Read/validate/profile in-memory CSV/XLSX | Parsing correctness, bounds, no silent data loss |
| `databuddy.py` | Coordinates questions and responses | Correct routes, retries, preserved evidence and status |
| `conversation_state.py` | In-memory history | Isolation, clipping, clear/reset and last-success context |
| `message_handler.py` | Routing, clock, conversation/explanation | Fallback precedence, malformed routing, no fabricated context |
| `analyst.py` | Prompt assembly and model-facing tasks | Important evidence retained when context is clipped |
| `llm_clients.py` | Groq/Mistral SDK boundary | Safe errors, retries, timeouts, tokens and actual fallback rules |
| `executor.py` | Worker launch and JSON result validation | Minimal env, disposable files, limits, process cleanup |
| `execution_policy.py` | Shared basic AST rules | Useful restrictions, consistency, common demo false positives |
| `_runner.py` | Generated computation/chart worker | Imports, print handling, actual evidence, serialization limits |
| `prompts/` | Generation/routing/narration instructions | Aligned with allowed behavior; no privacy or security promises |
| `tests/` | Offline regression suite | Meaningful assertions and mock boundaries |
| `examples/` | Synthetic demonstration data | Known results, no private customer data |
| `requirements*.txt` | Direct/dev pins and Windows snapshot | Reproducibility claims and platform limits |
| `docs/` | Current guides and historical references | Behavior matches source; no secrets or unsupported claims |

Core interface: `DataBuddy(source, filename=None).ask(question)` returns an `AskResult` with `answer`, optional `chart_json`, `chart_description`, `visualization_suggestion`, `result_text`, `code`, and `status` (`success`, `partial`, `error`, `clarification`). No HTTP API was added.

## 7. Reported prior validation: verify, do not assume

Previous environment: Windows, Python 3.11.9. Packages were already installed; no clean-environment install or package upgrade was performed during the readiness work.

| Test area | Previously reported count |
| --- | ---: |
| Dataset loading/profiling | 22 |
| Worker/execution | 36 |
| Analysis and conversation | 22 |
| Providers and UI state helpers | 20 |
| Streamlit behavior | 6 |
| Synthetic demo | 8 |
| Terminal behavior | 2 |
| **Combined suite** | **116 passing tests** |

The reported full run took 29.38 seconds. Timing is informational and will vary. Analysis/conversation tests were rerun after the final prompt-policy alignment and passed.

Other previous checks: dependency consistency, syntax parsing of 25 Python/test files, diff whitespace, current-document links, known-key comparison, ignore rules, original-backup identity, and independent source review. An additional offline HTML-download check passed.

Important limits:

- No live provider inference/authentication/model-access test.
- No real-browser PNG-download/mobile visual test.
- No clean-environment installation or Linux-host test.
- No dependency-vulnerability audit or public penetration test.
- No deployment or replacement frontend/API.
- No OS-enforced sandbox, network isolation or memory cap for arbitrary generated Python.

## 8. Review protocol and evidence standard

For each checkbox below, record `PASS`, `FAIL`, `NOT VERIFIED`, `NOT APPLICABLE` or `DEFERRED` in the report. An unchecked checkbox is not automatically a defect.

- `PASS`: you performed a check and can cite the source location, command/test or observed behavior.
- `FAIL`: you reproduced a mismatch or failure and can describe its impact.
- `NOT VERIFIED`: source/environment/account access or approval was insufficient.
- `NOT APPLICABLE`: the feature is absent by agreed scope; explain why.
- `DEFERRED`: it belongs to a later owner-approved stage, not current readiness.

Separate code inspection, mocked tests, real local computation, browser interaction and live model inference. They establish different things. Do not report mocks as proof of model availability or reasoning quality. Do not report static rules as proof of a hardened security boundary.

Do not run destructive or invasive tests on the host. Use synthetic inputs and temporary directories. Test obvious file/network rejection through validation or controlled mocks; do not attempt to exfiltrate local files, connect to internal services, exploit the machine or exhaust host resources.

## 9. Phase A: confirm scope, baseline and environment first

- [ ] Read `AGENTS.md` before any action.
- [ ] Confirm the active path is `D:/projects/databuddy 2.0`.
- [ ] Confirm the original and previous folders are not being used as workspaces to edit.
- [ ] Capture branch, HEAD and working-tree status before review.
- [ ] Recognize that the fixes are uncommitted and include untracked files.
- [ ] Inspect tracked differences and enumerate new non-ignored files separately.
- [ ] Do not reset, clean, discard, stage or commit the existing work.
- [ ] Record the actual Python interpreter path, Python version and operating system.
- [ ] Check direct dependency versions against `requirements.txt`.
- [ ] Treat `requirements-lock-windows.txt` as a tested installed-environment snapshot, not a universal lockfile.
- [ ] Confirm no install/upgrade is needed before using the existing environment; if it is needed, report the requirement before changing it.
- [ ] Run dependency consistency checks and record errors without revealing configuration values.
- [ ] Confirm no existing `.env` is overwritten by quick-start commands.

Suggested non-mutating commands, from the active folder:

```powershell
Set-Location -LiteralPath 'D:\projects\databuddy 2.0'
git status --short --branch
git rev-parse HEAD
git diff --stat
git diff --check
git ls-files --others --exclude-standard
python --version
python -m pip check
```

These commands do not substitute for source inspection. Do not paste complete private configuration or datasets into command output or reports.

## 10. Phase B: rerun the offline regression suite

- [ ] Read `pytest.ini` and `tests/conftest.py` before running tests.
- [ ] Confirm tests do not intentionally consume real model quota.
- [ ] Check that configured keys are replaced in tests rather than printed.
- [ ] Understand the network guard: it patches parent-process socket connections; Windows asyncio loopback is permitted. It is not a host firewall and does not automatically cover every child process or networking API.
- [ ] Run the combined suite and record exact passed/failed/skipped counts and duration.
- [ ] Investigate a different test count rather than blindly comparing with 116.
- [ ] Inspect all failures, warnings and skipped tests; do not suppress them to achieve a green result.
- [ ] Check at least one real aggregate and one real chart go through the worker, rather than every layer being mocked.
- [ ] Check that tests exercise error branches as well as happy paths.
- [ ] Check whether mocks are placed at realistic boundaries and can hide SDK/configuration mistakes.
- [ ] Do not add assertions that merely repeat implementation details instead of checking user-visible outcomes.

```powershell
python -B -m pytest -q
```

Targeted commands when investigating a finding:

```powershell
python -B -m pytest tests/test_datasets.py -q
python -B -m pytest tests/test_executor.py -q
python -B -m pytest tests/test_analysis.py tests/test_conversation.py -q
python -B -m pytest tests/test_providers.py tests/test_ui_state.py -q
python -B -m pytest tests/test_streamlit.py -q
python -B -m pytest tests/test_demo.py tests/test_cli.py -q
```

## 11. Phase C: loading, validation and data correctness

### Formats and limits

- [ ] UI and Python both enforce 20 MiB, not just the browser widget.
- [ ] At-limit and over-limit behavior is tested without allocating excessive memory.
- [ ] CSV is accepted and identified as the main demo format.
- [ ] XLSX is accepted, using the first sheet; this restriction is visible/documented.
- [ ] XLS, XLSM, XLSB and arbitrary extensions are not falsely advertised as supported.
- [ ] Extension checks are case-insensitive and malformed binary content is handled cleanly.
- [ ] Empty files, whitespace-only files and header-only files have understandable outcomes.
- [ ] Malformed quoting and inconsistent row lengths are not silently ignored.
- [ ] Missing/duplicate headers are handled consistently.
- [ ] Row, column, CSV cell-length and workbook-expansion limits match documentation.
- [ ] A file below 20 MiB can still hit processing limits, and the resulting error explains that distinction.

### Parsing and values

- [ ] UTF-8 and UTF-8 BOM data work.
- [ ] Latin-1 fallback is disclosed, rather than silently promising correct encoding for every file.
- [ ] Comma-separated input is the supported CSV dialect; other delimiters are not silently promised.
- [ ] Leading-zero identifiers remain text where intended, without forcing ordinary numeric metrics into unusable strings.
- [ ] Default missing-value markers and empty fields are documented and checked against demo expectations.
- [ ] Zero, negative numbers, decimals, missing values and mixed numeric/text columns produce sensible profiles.
- [ ] Completely valid ISO date columns convert correctly.
- [ ] Ambiguous, mixed or invalid date-like values stay intact and produce an import notice.
- [ ] Date conversion does not silently replace valid source text with missing data.
- [ ] Profile clipping is explicit and does not pretend that omitted columns/details are available to the model.
- [ ] Very long names, values and wide datasets cannot create an unbounded prompt/profile.
- [ ] Bytes, binary streams and CLI paths all respect limits and preserve the expected filename.
- [ ] A provided stream's position is not unexpectedly destroyed.

### Replacement and failure behavior

- [ ] Same name + different content replaces the active dataset.
- [ ] Same name + same content does not unnecessarily reset the conversation.
- [ ] New valid dataset clears old dataset-specific chat/chart context.
- [ ] Failed replacement preserves the previously working dataset and displayed state.
- [ ] The interface clearly indicates which dataset remains active after failure.
- [ ] Rejected selected files are not reparsed on every chat/reset/rerun.
- [ ] Changing a rejected file's contents allows a new validation attempt.
- [ ] User-facing errors do not leak stack traces, private paths or raw provider bodies.

## 12. Phase D: known answers and analysis behavior

Use `examples/demo_sales.csv`. It contains four synthetic rows and does not require the private uploaded dataset.

| Calculation | Expected result |
| --- | --- |
| Row count | 4 |
| Total sales | 1000 |
| Average sales | 250 |
| Total units | 20 |
| Sales by region | North 400; South 600 |
| Sales by product | Notebook 500; Pen 500 |
| Highest-sales product | A tie between Notebook and Pen |
| Sales by month | January 2026: 300; February 2026: 700 |
| Missing sales values | 0 |

- [ ] Check calculations against independent direct pandas/Python results.
- [ ] Grouping, sorting and filters operate on the active dataset.
- [ ] Ties are not reported as a single clear winner.
- [ ] Empty filtered results are distinguished from zero, missing and execution failure.
- [ ] The displayed result is actual worker output, not a model's guessed calculation.
- [ ] Clear follow-ups use the latest relevant analysis rather than unrelated casual facts.
- [ ] A remembered preference does not become a default dataset filter.
- [ ] Unsupported questions and absent computed results produce clarification or a clear limitation.
- [ ] A failed execution is not sent for a misleading success narrative.
- [ ] A successful calculation survives a narration outage or empty response.
- [ ] Both UI and CLI display the preserved evidence on partial success.
- [ ] A failed request does not erase the last successful analysis needed for explanation.
- [ ] Blank/overlong questions are handled before expensive work.
- [ ] Code retries are bounded and only happen for the appropriate failure path.
- [ ] Prompts retain the question and computed evidence when clipping lower-priority context.
- [ ] Suggestions are off by default, avoiding an unnecessary extra model call.
- [ ] If suggestions are enabled, their failure does not discard the answer.
- [ ] Local clock and direct remember paths avoid unnecessary provider calls.
- [ ] Malformed router output falls back to clear local rules without crashing.

Live natural-language interpretation is not proven by deterministic tests. Mark actual model reasoning/routing quality separately unless the owner authorizes the optional live phase.

## 13. Phase E: chart correctness, evidence and downloads

- [ ] At least a bar chart, line chart and a reasonable distribution/correlation example work through generated-code-compatible paths.
- [ ] Region bar-chart evidence matches North 400 and South 600.
- [ ] Chart-only code receives actual plotted-value evidence when it does not explicitly return a result table.
- [ ] Narration is not asked to infer numbers solely from dataset profiles or code.
- [ ] Sampled/truncated evidence is labeled and not presented as a complete dataset.
- [ ] Explanations distinguish visible association/trend from an unsupported causal claim.
- [ ] Failed narration preserves a successfully generated chart and its follow-up context.
- [ ] A missing figure or failed chart is not marked as a successful analysis.
- [ ] Modifying a chart without chart history gives a clear response.
- [ ] A valid chart modification keeps relevant data context and changes the requested aspect.
- [ ] Chart history is bounded and clears on reset/replacement/removal.
- [ ] Large chart JSON is bounded; external images/geographic resources are rejected by the implemented basic checks.
- [ ] Prompt-only point limits are distinguished from actual runtime-enforced limits.
- [ ] Merely rerendering chat does not regenerate expensive server PNGs.
- [ ] The chart camera button is configured for browser PNG download.
- [ ] Preparing interactive HTML is an explicit action and produces a usable download.
- [ ] HTML export discloses that it contains plotted data and needs internet for Plotly's CDN.
- [ ] Message/chart widget identities remain correct when history is trimmed or rerendered.
- [ ] Headless export preparation is not mislabeled as a real-browser download test.

## 14. Phase F: runner reliability and simple security

This phase assesses agreed basic safeguards, not certification against arbitrary hostile Python. Do not attempt host escape/exfiltration or destructive stress tests.

- [ ] Parent and worker use the same code policy.
- [ ] Empty, invalid and oversized code produces a clear bounded failure.
- [ ] Permitted pandas/NumPy/Plotly imports work consistently with validation.
- [ ] Unapproved, private and wildcard imports are handled according to the documented policy.
- [ ] A harmless print does not corrupt the structured result channel.
- [ ] Diagnostic print and stdout/stderr are bounded.
- [ ] Obviously unsafe read/write/file/network/private-attribute paths are rejected before execution.
- [ ] Aliased and keyword-expanded `to_string` attempts are covered by rejection tests.
- [ ] Prompts instruct boolean masks instead of blocked `query`/`eval` paths and do not ask for blocked formatting methods.
- [ ] Useful ordinary calculations are not unnecessarily blocked; report concrete false positives.
- [ ] Worker receives a minimal environment without application API keys.
- [ ] Worker does not import core config or discover `.env` through ordinary application bootstrap.
- [ ] Worker starts in a fresh temporary working directory and isolated Python mode.
- [ ] The actual timeout path terminates/reaps the worker.
- [ ] Temporary worker transport files are removed after normal completion, handled failure and timeout.
- [ ] Parent accepts validated JSON, not worker-provided pickle output.
- [ ] Input pickle is parent-generated internal transport, never an accepted user upload.
- [ ] Parent validates output structure, text type, return status and chart sizes.
- [ ] Numeric formatting preserves useful precision and marks truncation.
- [ ] Failure output cannot grow without bound or expose credentials from SDK responses.
- [ ] Documentation explicitly says the worker shares the host account and lacks OS memory/network isolation.
- [ ] No public-safe/sandbox guarantee is inferred from passing static checks and tests.

If you identify an easy unsafe path, report a harmless validation-only reproduction or a controlled synthetic test. Explain whether it violates a stated basic rule or is an already-disclosed limitation. Do not use the finding to implement a large sandbox platform without an owner decision.

## 15. Phase G: providers, configuration, quota and errors

Use fake clients/errors for this phase. Real keys should not be printed, changed or transmitted.

- [ ] Core `config.py` does not import Streamlit.
- [ ] Streamlit Secrets are loaded at the UI boundary before core configuration is initialized.
- [ ] Only allowlisted scalar settings are copied from Streamlit Secrets.
- [ ] Environment/Secrets/local `.env` precedence is predictable and documented.
- [ ] Missing secrets files do not break a valid local `.env` setup.
- [ ] Invalid numeric settings fail with a useful message that does not echo sensitive values.
- [ ] Groq-only data analysis uses a working local routing path.
- [ ] Mistral-only analysis uses the configured fallback path.
- [ ] No-provider configuration disables model-backed UI input with a clear message.
- [ ] Ordinary chat/explanation requirements are described accurately when Mistral is absent.
- [ ] Missing keys, bad authentication, unavailable models, temporary outages and quota limits are distinguishable enough to act on.
- [ ] SDK response bodies and credentials are not concatenated into displayed errors.
- [ ] Groq SDK retries are disabled when application retries are used.
- [ ] Mistral SDK retries are explicitly controlled and not silently multiplied.
- [ ] Per-attempt timeouts and output-token caps are passed using installed SDK-supported arguments.
- [ ] Shared request-budget behavior is tested, including expiry before another provider call.
- [ ] Documentation avoids claiming a strict whole-process wall-clock or billing guarantee that the implementation does not provide.
- [ ] Transient Groq failure can fall back to Mistral, while permanent configuration/authentication errors are not silently hidden.
- [ ] Model defaults are examples/configuration values, not a claim that a particular account can access them.
- [ ] No code enables paid billing, buys credits or silently upgrades an account.
- [ ] Free-tier availability and existing account billing remain explicitly external constraints.

## 16. Phase H: session lifecycle, privacy and display

- [ ] Uploads are parsed from bytes/streams without creating saved upload files.
- [ ] Conversations have no active disk save/load or database path.
- [ ] No active Gemini summarization call remains; old credentials are not needed.
- [ ] Recent-turn history, displayed messages and chart history are bounded separately.
- [ ] Sessions do not share a module-global DataBuddy/DataFrame/conversation instance.
- [ ] Reset clears question/answer/chart/last-analysis context while keeping the dataset.
- [ ] Remove dataset clears dataset state, messages and uploader state.
- [ ] A new CLI run/session does not restore a prior conversation.
- [ ] Legacy `.databuddy_state` files are neither loaded nor mistaken for newly saved history.
- [ ] Closing a tab is not falsely described as synchronous server-memory deletion.
- [ ] Temporary worker files, OS crash behavior and provider retention are distinguished from app-level persistence.
- [ ] Dynamic filenames and suggestions are escaped before raw HTML insertion.
- [ ] Column/value display uses appropriate native text/table handling.
- [ ] Standard Markdown rendering is not equated with a complete external-content/network policy.
- [ ] Provider disclosure includes samples, statistics, category values, results and conversation context as applicable.
- [ ] `SAMPLE_ROWS=0` is not falsely described as sending no dataset-derived information.
- [ ] Debug logs contain metadata rather than raw prompts, rows, answers or credentials.
- [ ] `.env` variants, `.streamlit/secrets.toml`, uploads and saved-state directories are ignored.
- [ ] `.env.example` contains placeholders only.
- [ ] No known real credentials are present in tracked/new public files or the review report.
- [ ] Any credential scan is described accurately: known-value matching is not proof that every possible unknown credential was detected.
- [ ] No private CSV, conversation or `.env` is sent to an external scanner or model for this review.

## 17. Phase I: interface and terminal usability

Headless UI checks should use Streamlit's existing AppTest support where available. No redesign is requested.

- [ ] Initial page renders with keys absent as well as present/faked.
- [ ] UI text/icons have correct encoding; no mojibake or invalid icon values.
- [ ] Upload help matches actual formats, size limits, first-sheet behavior and session-only scope.
- [ ] Loading/error feedback names the real task rather than promising unsupported progress/cancellation.
- [ ] Active dataset name/counts/preview update after successful replacement.
- [ ] Failed replacement leaves a clearly identified previous dataset active.
- [ ] Evidence and code are accessible from the response without requiring a separate tool.
- [ ] Reset/removal labels match their actual effects.
- [ ] Reasonable histories do not duplicate messages, charts or exports on reruns.
- [ ] Terminal `/state`, `/reset`, `/quit`, empty input and EOF behave sensibly.
- [ ] Terminal displays import notices and computed evidence on partial success.
- [ ] Terminal errors are understandable and avoid raw provider bodies.

### Optional real-browser pass: not previously completed

Ask the owner before starting a manual server session, and stop any server started for review when finished. Do not make live model calls unless separately authorized. Use synthetic data and offline/mocked results where practical.

- [ ] Upload/preview/reset/remove work in the actual browser.
- [ ] Chart hover, zoom and PNG camera download work.
- [ ] Prepared HTML downloads and opens with the stated internet requirement.
- [ ] Long filenames/messages and narrower windows remain usable.
- [ ] Keyboard focus, readable labels, contrast and error placement are checked at a practical demo level.
- [ ] Record which browser/viewport was used and what was not tested.

The optional command is:

```powershell
python -m streamlit run web_app.py
```

Do not claim that the current layout is a newly designed dedicated web app.

## 18. Phase J: documentation and dependency truthfulness

- [ ] README has no duplicated project description and no stale 50 MB limit.
- [ ] Current docs consistently describe CSV/XLSX, first-sheet XLSX and unsupported Excel variants.
- [ ] Current docs do not claim persisted CLI history or Gemini summaries.
- [ ] Current docs distinguish original backup, active checkout and the older previous folder.
- [ ] Current docs distinguish a UI-independent core from a completed HTTP API.
- [ ] Security/privacy limits agree with the actual code.
- [ ] Private provider settings are not presented as verified free access.
- [ ] Setup commands do not overwrite an existing `.env` or unexpectedly change the current environment.
- [ ] Exact package pins match the environment actually exercised.
- [ ] The Windows snapshot is not advertised as a fresh-install/Linux guarantee.
- [ ] Removed Google GenAI/Kaleido dependencies are not required by an active import path.
- [ ] Local Markdown links resolve; root legacy guides point to current documentation.
- [ ] Historical material is clearly labeled and not used as acceptance criteria.
- [ ] Work log says what changed, why, what was checked and what remains uncertain.
- [ ] Validation counts/outcomes are historical evidence and not falsely attributed to your new review.
- [ ] Any confirmed finding or later approved fix updates the relevant docs, not only a chat message.

## 19. Optional verification that remains outside the default review

### Live provider demonstration

Previously not performed. Requires an owner decision because even free calls consume limited quota and transmit prompt content.

If authorized, use only the synthetic CSV and a very small agreed call budget. Check actual credentials/model access, one aggregate, one chart and one follow-up. Record account-dependent failures honestly. Do not deliberately exhaust quota, send private data, change billing settings or add paid fallback services.

### Clean installation and other operating systems

Previously not performed. A successful run in an existing environment does not prove clean installation or Linux-host compatibility. Propose an isolated temporary virtual environment if this check is worth doing; do not upgrade the owner's working interpreter. Report platform-specific constraints before choosing a deployment target.

### Dependency-vulnerability review

Previously not performed. If suggested, distinguish a lightweight relevant dependency audit from a comprehensive security program. Do not upload private source/data to a third-party service or install new audit tooling without agreement. Do not call version pinning proof of vulnerability freedom.

### Public hosting and stronger isolation

Deferred. The intended demo is trusted, but unrestricted anonymous upload/code execution changes the threat model. Any public exposure plan needs a fresh scope decision. Do not silently build containers, accounts, queues, databases or infrastructure during this review.

## 20. Items intentionally deferred or excluded

| Item | Current decision | Reconsider only when |
| --- | --- | --- |
| Replacement frontend/design | Later stage; do not build now | Owner accepts readiness review and starts design |
| HTTP API | No API in this change | Future frontend requires a defined transport layer |
| Database/persistent datasets/chats | Excluded | Owner changes session-only requirement |
| Login/accounts/team roles | Excluded | Audience and data-ownership needs change |
| Queues/distributed workers/autoscaling | Excluded | Actual workload shows the simple process approach is inadequate |
| Enterprise monitoring/billing/admin systems | Excluded | A different product and operating budget is approved |
| More Excel engines/sheet-selection features | Not a current priority | Demo requirements justify the added complexity |
| Additional cloud/data-source integrations | Excluded | Explicit feature request |
| Hardened arbitrary-code sandbox | Not implemented; limitation disclosed | Exposure changes beyond trusted demos |
| Paid infrastructure/provider upgrades | Not authorized | Owner explicitly changes zero-budget requirement |
| Full accessibility certification or public security certification | Not claimed | Appropriate later release target is agreed |
| Commit/push/deployment | Not authorized by this handoff | Owner explicitly requests it after review |

These are not automatic failures. Report a scope-changing prerequisite when it is necessary for a proposed deployment, but do not confuse it with an already-agreed local-demo bug fix.

## 21. Required second-opinion report format

Please produce a concise executive recommendation followed by detailed evidence. Use `docs/ANTIGRAVITY_REVIEW.md` or return the report in chat if file output is unavailable.

### A. Review context

- Actual folder, branch, HEAD, date, OS, interpreter and dependency setup.
- Scope read and permissions respected.
- Commands run and whether any environment changes occurred.
- What you inspected versus what you could not verify.

### B. Findings, most important first

For every finding provide:

| Field | Required detail |
| --- | --- |
| ID and severity | Stable ID and practical impact for this trusted-demo scope |
| Status | Reproduced, source-confirmed, suspected or not verified |
| Location | Actual file/function and current line number where useful |
| Trigger | Minimal synthetic reproduction or precise code path |
| Expected/actual | What should happen and what happened |
| Impact | Wrong answer, demo breakage, data loss, exposure, wasted quota or maintenance burden |
| Proposed fix | Smallest understandable fix; avoid unnecessary architecture |
| Regression check | How to prove the fix addresses the problem |
| Cost/scope | Dependencies, account costs, tradeoffs and whether owner approval changes scope |

Suggested severity meanings:

- **P0:** immediate serious exposure/data destruction or a dangerous action that must stop. Do not use this label for a deferred enterprise feature alone.
- **P1:** reproducible core-demo failure, wrong result, broken recovery or violation of an agreed basic safeguard.
- **P2:** meaningful reliability, clarity or usability problem with a workaround.
- **P3:** optional improvement or later design suggestion.

Do not invent findings. If none are found in a category, state the checks and their limits.

### C. Test and checklist results

Group PASS/FAIL/NOT VERIFIED/NOT APPLICABLE/DEFERRED results by phases A through J. Include exact test counts, important manual observations and any fresh-install/live-provider/browser checks that were not done.

### D. Suggestions requested from you

Please give an independent opinion on:

1. The top five worthwhile improvements for this specific personal project.
2. Any feature or abstraction you would remove or simplify.
3. Any misleading test, incomplete assertion or mock that should be strengthened.
4. Whether current limits are reasonable for the supplied demo and zero-budget constraints.
5. Whether provider calls, retries or suggestions could be reduced further without harming the demo.
6. Whether evidence, errors and reset behavior are clear enough for a recruiter to understand.
7. Whether the privacy wording is honest and understandable.
8. Whether the docs are useful to a new contributor and properly distinguish history from current behavior.
9. Any small, high-value quality-of-life change worth doing before design.
10. Any new risk that only appears when moving to a separate frontend/API, clearly labeled as future work.

For each suggestion, classify it as `fix before demo`, `useful now`, `later design`, or `out of scope`. Include effort (small/medium/large), new dependencies/cost and the simplest alternative. If your suggestion changes the agreed scope, call that out explicitly.

### E. Final recommendation

Choose and justify one:

- `Proceed to design`: no reproduced issue prevents the agreed trusted demo, with unverified areas listed.
- `Proceed with documented limitations`: acceptable for a controlled demo, with explicit gaps and owner decisions.
- `Fix before design`: list specific blocking findings and the minimal ordered fix plan.

Passing 116 tests is not by itself a readiness decision. A small number of reproducible important findings matters more than a large generic checklist.

## 22. Planned work after Antigravity's review, in order

1. **Owner reviews the second opinion.** Separate confirmed defects, optional suggestions and scope changes.
2. **Agree on a small follow-up fix list.** Retain the personal-demo, session-only, 20 MiB and zero-budget requirements.
3. **Implement only approved follow-up work.** Stay in `databuddy 2.0`; leave the original backup alone; update docs as each change is made.
4. **Recheck affected behavior.** Add meaningful regression coverage for reproduced defects, rerun appropriate checks and record results.
5. **Repeat the synthetic demonstration.** Actual provider/browser checks stay separately labeled and require the owner's decision where quota/manual setup is involved.
6. **Decide on a Git checkpoint.** Local commit/review/push is a future owner-authorized action, not part of this handoff. Do not discard uncommitted fixes.
7. **Begin design discussion.** Choose user journeys, information layout, visual direction and frontend/backend transport only after the owner starts that stage.
8. **Plan the dedicated web app.** Revisit upload/session ownership, temporary state, code execution exposure and free-hosting limits in the chosen architecture.
9. **Build only after design/implementation is authorized.** Preserve current behavior with tests; do not introduce persistent storage/accounts unless requested.
10. **Check deployment feasibility separately.** A local pass is not proof a free hosting provider can run the worker or fit the dataset in RAM. No deployment is currently approved.

## 23. Acceptance gate for ending this review

- [ ] You reviewed the actual working tree including new files.
- [ ] Scope and backup/private-file boundaries were respected.
- [ ] Offline test results and independent observations are recorded.
- [ ] Confirmed defects are separated from hypotheses and deferred features.
- [ ] Documentation claims were compared with code and behavior.
- [ ] Unverified live-provider/browser/install/platform areas remain clearly labeled.
- [ ] Basic safeguards are not described as complete isolation or public security certification.
- [ ] Suggestions are prioritized for this project's benefit, cost and simplicity.
- [ ] The owner has a clear next-step recommendation and an ordered minimal fix plan if needed.
- [ ] No application changes, paid calls, commits, pushes, deployment or replacement frontend were performed under this review-only brief.

**Final request:** Be candid, specific and practical. Challenge the implementation and this checklist where warranted. Tell us what we missed, what we overcomplicated, what we should fix first, and what can safely wait for the later design stage.

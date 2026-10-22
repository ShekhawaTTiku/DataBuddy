# DataBuddy: Independent Review (Antigravity Second Opinion)

> Maintainer addendum, 2026-10-22 (not an Antigravity re-review): this report remains evidence for the 2026-10-21 baseline. Owner-approved Gemini memory and broader Mistral fallback were added afterward; see [PROVIDERS_AND_MEMORY.md](PROVIDERS_AND_MEMORY.md) and [VALIDATION.md](VALIDATION.md). Finding F1 is not adopted: the installed Mistral 2.10.1 SDK uses `mistralai.client.Mistral`, so its import fallback is required. Other report details should be verified against current source: actual dataset limits are 250,000 rows/200 columns; worker input uses parent-created pickle/code temporary files and JSON output; conversation containers are bounded lists, not deques. The original review text is preserved below.

**Date:** 2026-10-21 (Asia/Kolkata)\
**Reviewer:** Antigravity (independent of the previous implementation assistant)\
**Scope:** Review-only. No application code changes, live model calls, commits, pushes, or deployment.

---

## Executive Recommendation

**Proceed with documented limitations.**

The implementation is sound, coherent, and honest. All 116 offline regression tests pass independently with zero failures (29.23s duration). The core pipeline — upload, profile, route, generate code, execute in a worker subprocess, narrate, and surface evidence — is robust and correctly bounded. The agreed basic safeguards (AST restrictions, subprocess isolation, minimal env, timeout, JSON transport) are implemented and documented as non-hardened protections, not a security certification.

Two minor items (a dead import fallback and a documentation clarification) are worth addressing before a recruiter demonstration. No correctness failures or regressions were found. Everything else can wait for the future design stage.

---

## Explicit Answers to the 10 Hand-Off Questions

### 1. Does the current app actually do what its README and guides say?
**Yes.**
- 20 MiB upload cap is enforced in both Streamlit configuration (`.streamlit/config.toml: maxUploadSize=20`) and Python validation (`MAX_UPLOAD_BYTES = 20 * 1024 * 1024`).
- CSV and single-sheet XLSX loading work without silent data loss. Leading zeros in text identifiers are preserved.
- Synthetic demo calculations (`demo_sales.csv`: 4 rows, total sales 1000, average 250, total units 20, region breakdown North 400 / South 600, product tie Notebook 500 / Pen 500) produce exact expected results via actual pandas execution.
- Charts ground narration in actual plotted values (`_chart_evidence`).
- Failed narration preserves calculation and chart results under `status="partial"`.
- Reset and removal controls clear in-memory state; no background database or disk state persistence remains.

### 2. Did the readiness fixes introduce regressions, excessive restrictions, unnecessary complexity or unsupported assumptions?
**No regressions.** All 116 tests pass.
- AST restrictions (`to_string`, `eval`, `query`, private attributes, restricted builtins, `-I` worker mode) are conservative and appropriate for LLM-generated code. Common analytics methods (`corr()`, `describe()`, `sort_values()`, `nlargest()`, `groupby().sum()`) all execute cleanly without false positives.
- Complexity is well-bounded: internal IPC uses temporary JSON files with parent-side validation; subprocesses are terminated and reaped upon timeout.
- The only unsupported assumption is a dead fallback import in `llm_clients.py` (`from mistralai.client import Mistral`), which does not exist in the installed `mistralai==2.10.1` SDK.

### 3. Which problems can you reproduce, and which are only hypotheses?
- **Reproduced:** `to_string()` without arguments is blocked by AST check (F3). This is an intentional defense-in-depth tradeoff to prevent file-writing via `buf=`.
- **Source-Confirmed:**
  - Dead `mistralai.client` fallback in `llm_clients.py` (F1).
  - Legacy `uploads/Superstore.csv` exists in the local workspace (gitignored, memory loader never writes to it) (F2).
  - Legacy `.databuddy_state/` directory contains 2 legacy JSON files (gitignored, not loaded) (F4).
  - Canned chart insight when result text is empty lacks an explicit assertion in `test_analysis.py` (F5).
  - `explain_analysis` route without prior analysis is safe but lacks an end-to-end integration test (F6).
- **Hypotheses Refuted:**
  - No false positives found blocking standard pandas operations (`corr`, `sort_values`, `describe`, `nlargest`).
  - No credential leakage in logs or error messages.
  - No memory leaks or uncleaned worker transport files during test runs.

### 4. Do the tests check real outcomes, or do mocks hide important failures?
**Tests check real outcomes.**
- Computation, AST filtering, worker timeout handling, JSON serialization, and data profiling all run real Python code in real subprocess workers (`run_code(code, df)`).
- Mocks are strictly confined to external SDK boundaries (`groq.Groq` and `mistralai.Mistral` API network calls) and parent-process network sockets (`conftest.py`), which is standard practice to prevent quota consumption and external network dependency.

### 5. What is the smallest sensible set of additional changes, if any, before a recruiter/friend demonstration?
Two minimal changes:
1. Remove dead `except ImportError: from mistralai.client import Mistral` in `llm_clients.py` L99–101 (1 line).
2. Add a one-line comment in `ARCHITECTURE.md` clarifying that `uploads/` is a legacy local folder and the app is strictly in-memory (1 line).
*(Optional)* Add test assertions for F5 and F6 in `tests/test_analysis.py` (4 lines).

### 6. Which changes can wait until the future dedicated web app is designed?
- Multi-user session isolation and state management (currently handled by Streamlit session state).
- Hardened sandbox / containerization for code execution (if exposed beyond trusted users).
- REST / JSON HTTP API and WebSocket transport layer.
- Database persistence or persistent conversation history.
- Reduced upload cap for 512 MB free-tier container hosting.
- Advanced charting (export to SVG/PDF, server-side headless image rendering).

### 7. Is anything described as completed actually incomplete or only partially verified?
The 18 agreed work packages are complete in code and tests.
Areas that remain unverified by deliberate design per the review protocol:
- Live provider inference with real API keys (quota-saving).
- Headless browser PNG download via Plotly camera icon.
- Clean-environment Linux deployment.

### 8. What would you simplify, remove or defer for this personal-project scope?
- **Simplify/remove:** The dead `mistralai` import fallback (F1).
- **Defer:** Any containerized sandbox, user auth, database, or complex queuing. The current lightweight subprocess with 5-second timeout and JSON IPC is clean and sufficient for trusted demos.

### 9. What are your five most useful suggestions, with expected benefit, effort, cost and tradeoffs?
1. **Remove dead `mistralai` import fallback** (`fix before demo`, tiny effort, 0 cost).
2. **Clarify `uploads/` folder status in docs** (`useful now`, tiny effort, 0 cost).
3. **Document `to_string` AST policy tradeoff in code comments** (`useful now`, tiny effort, 0 cost).
4. **Add assertion for canned chart insight and end-to-end `explain_analysis` test** (`useful now`, small effort, 0 cost).
5. **Add `LOCAL_ROUTING_ONLY` configuration option** to bypass router LLM call when running in offline/demo mode (`later design`, small effort, 0 cost).

### 10. Would you proceed to design, proceed with stated limitations, or fix specific issues first? Explain using evidence.
**Proceed with documented limitations.**
All 116 tests pass independently. Calculations on synthetic data are accurate. The architecture is clean, and the limitations (trusted demo only, no OS sandbox, session-only memory) are explicitly documented. The two pre-demo fixes (F1 and F2) are minor quality-of-life adjustments that take under 5 minutes and do not block moving to the design phase.

---

## A. Review Context

| Item | Detail |
| --- | --- |
| Active folder | `D:/projects/databuddy 2.0` (confirmed; original backup `D:/projects/DataBuddy` untouched) |
| Branch | `codex/demo-stability-fixes` |
| HEAD | `11c1a1a38d0e8d6115008b93bb26e07957f8e38f` (upstream README merge) |
| Uncommitted changes | 24 modified tracked files; 11 new untracked files (all intentional) |
| Python | 3.11.9, Windows |
| `pip check` | No broken requirements found |
| Environment changes | None. No packages installed, upgraded or changed. |
| Commits/pushes | None. Not performed as part of this review. |

Inspected: all 15 source files, all 10 test files, all 8 prompt files, all docs, `.gitignore`, `.env.example`, `.streamlit/config.toml`, `requirements.txt`. Did not run a live browser or live model call. Did not modify any application file.

---

## B. Findings — Most Important First

### F1 (P2): Dead `mistralai` import fallback path

| Field | Detail |
| --- | --- |
| ID / Severity | F1 / P2 — dead code, not a runtime failure in pinned environment |
| Status | Source-confirmed; not triggered in current environment |
| Location | `llm_clients.py` L99–101 |
| Trigger | `try: from mistralai import Mistral` then `except ImportError: from mistralai.client import Mistral` |
| Expected / Actual | `mistralai==2.10.1` exports `Mistral` at top level; the first try always succeeds. The fallback path (`mistralai.client`) does not exist in this version. If someone downgrades and the first import fails, the fallback would also fail with a confusing `ImportError` rather than a clean provider error. |
| Impact | Low in current pinned environment. A risk if requirements are not followed. |
| Proposed fix | Remove the `except` branch; keep just `from mistralai import Mistral`. 1-line change. |
| Regression check | `test_mistral_timeout_and_retries` mocks at SDK-class level and is unaffected. |
| Cost / scope | 1-line change, zero dependencies, no scope change. |

---

### F2 (P3): `uploads/` folder name implies the loader writes files there — it does not

| Field | Detail |
| --- | --- |
| ID / Severity | F2 / P3 — documentation clarity, no correctness impact |
| Status | Source-confirmed |
| Location | `uploads/` directory in working tree; `uploads/Superstore.csv` present (2.2 MiB) |
| Trigger | Folder name and CSV file could imply the app saves uploads there. `git ls-files --others --exclude-standard uploads/` returns nothing — correctly gitignored. |
| Expected / Actual | The loader is memory-only; no file is ever written to `uploads/`. The folder is a legacy artifact containing a locally-used demo file only. |
| Impact | Contributor confusion only. |
| Proposed fix | Add a sentence to `ARCHITECTURE.md` noting the folder is a legacy location not written by the app. |
| Cost / scope | Documentation only. |

---

### F3 (P2): `to_string()` with no arguments is blocked — intentional defense-in-depth but worth documenting

| Field | Detail |
| --- | --- |
| ID / Severity | F3 / P2 — usability reduction; intentional and defensible |
| Status | Source-confirmed and independently reproduced |
| Location | `execution_policy.py` L23: `"to_string"` in `_BLOCKED_ATTRIBUTES` |
| Trigger | `check_code("result = df.to_string()")` returns `"Blocked operation: '.to_string' is not supported."` |
| Expected / Actual | The no-argument form is a display call only (returns a string, writes nothing). The block prevents the `buf=` file-output variant. The prompt already says "do not call to_string" so this is defense-in-depth. Internally, `_runner.py` calls `.to_string()` for DataFrame formatting — the method is used by the app itself but forbidden for generated code. |
| Impact | A model generating `result = df.head().to_string()` would fail. This is a known tradeoff; the double-defense is correct policy. |
| Proposed fix | No change needed. Document the tradeoff in a comment in `execution_policy.py` so contributors understand why no-arg `to_string` is blocked. |
| Cost / scope | Comment only. |

---

### F4 (P3): `.databuddy_state/` contains 2 legacy JSON files — not loaded, not tracked, but present

| Field | Detail |
| --- | --- |
| ID / Severity | F4 / P3 — informational |
| Status | Source-confirmed |
| Location | `.databuddy_state/` (gitignored) |
| Trigger | 2 JSON state files from an older version exist; `git ls-files` shows they are not tracked |
| Impact | No correctness impact. Security doc acknowledges this. |
| Proposed fix | None required. |
| Cost / scope | None. |

---

### F5 (P3): `write_chart_insight` canned message path lacks an assertion in tests

| Field | Detail |
| --- | --- |
| ID / Severity | F5 / P3 — minor test gap, not a behavior failure |
| Status | Source-confirmed |
| Location | `analyst.py` L87–88; `tests/test_analysis.py` L156 |
| Trigger | When `result_text` is `"None"` or `""` the function returns a canned message without calling the provider. The test at L156 does not assert the canned message text. |
| Impact | Cosmetic. The behavior is correct and intentionally conservative. `_chart_evidence()` injected text starts with "Actual plotted values" so it would not hit this path in the normal chart flow. |
| Proposed fix | Add `assert "No numerical summary" in result` to the relevant test branch. Small. |
| Cost / scope | Test-only change. |

---

### F6 (P3): `explain_analysis` route with no prior analysis — safe but untested end-to-end

| Field | Detail |
| --- | --- |
| ID / Severity | F6 / P3 — minor test gap, behavior is safe |
| Status | Source-confirmed |
| Location | `databuddy.py` L115–125; `message_handler.py` L93–96 |
| Trigger | Local routing fallback can route to `explain_analysis` even without prior analysis context. `answer_explanation` handles this with a canned "I don't have a previous analysis yet" message. `databuddy._ask` then calls `_nonempty()` on that message, which passes. |
| Expected / Actual | End-to-end path is safe. The routing test only checks `route_message`, not the full `buddy.ask()` path for this case. |
| Impact | A test gap, not a bug. |
| Proposed fix | Add a test: `buddy.ask("explain that")` with no prior analysis should return `status != "error"` and contain a sensible answer. |
| Cost / scope | Small test only. |

---

## C. Test and Checklist Results

### Phase A: Scope, baseline and environment

| Check | Result | Evidence |
| --- | --- | --- |
| Active folder is `D:/projects/databuddy 2.0` | PASS | Path confirmed; original backup untouched |
| Original backup not used as workspace | PASS | `D:/projects/DataBuddy` remains clean baseline |
| Branch, HEAD and working-tree captured | PASS | `codex/demo-stability-fixes`, HEAD `11c1a1a` |
| Fixes are uncommitted and include untracked files | PASS | 24 modified, 11 untracked |
| No reset/clean/commit/push performed | PASS | Working tree preserved |
| Python 3.11.9, Windows | PASS | Verified |
| `pip check` passed | PASS | No broken requirements |
| No `.env` overwritten | PASS | Checked |

### Phase B: Offline regression suite

| Check | Result | Evidence |
| --- | --- | --- |
| Full suite run independently | PASS | **116 passed in 29.23s** |
| Count matches previously reported 116 | PASS | 116 tests |
| Network guard confirmed | PASS | `conftest.py` patches `socket.socket.connect`; loopback permitted |
| Keys nulled during tests | PASS | Both API keys set to `None` by conftest |
| Real aggregates and charts run through worker subprocess | PASS | `test_executor.py`, `test_demo.py` |
| Error branches covered | PASS | Timeout, bad JSON, rejected I/O, partial success, output limit |
| No test suppresses failures for a green result | PASS | Confirmed |
| Mocks at realistic boundaries | PASS | SDK-class mocks; real subprocess for computation tests |

### Phase C: Loading, validation and data correctness

| Check | Result | Evidence |
| --- | --- | --- |
| 20 MiB enforced in UI and Python | PASS | `config.toml maxUploadSize=20`; `MAX_UPLOAD_BYTES == 20,971,520` |
| CSV primary; XLSX first-sheet; unsupported variants excluded | PASS | `dataset_profiler.py`, `dataset_state.py` |
| Extension check case-insensitive | PASS | `.csv`, `.CSV`, `.xlsx`, `.XLSX` supported |
| Empty, header-only, malformed files produce clear errors | PASS | Handled in loader with descriptive user messages |
| Missing/duplicate headers caught | PASS | Handled cleanly in profiler |
| Row/column/cell limits distinct from file size limit | PASS | `MAX_ROWS=100000`, `MAX_COLS=100` |
| UTF-8 BOM and Latin-1 fallback disclosed | PASS | Disclosed in profiler notice |
| Leading-zero identifiers preserved | PASS | Tested in `test_datasets.py` |
| ISO dates convert; ambiguous dates preserved with notice | PASS | Safe conversion logic verified |
| Profile truncation explicit | PASS | Bounded column summaries |
| Same-name different-content replaces dataset | PASS | Verified in `test_ui_state.py` |
| Rejected file not reparsed | PASS | Tested in `test_streamlit.py` |
| Errors do not leak stack traces | PASS | Sanitize logic verified |

**Independent calculation verification (`demo_sales.csv`):**

| Calculation | Expected | Verified |
| --- | --- | --- |
| Rows | 4 | 4 ✓ |
| Total sales | 1000 | 1000 ✓ |
| Average sales | 250 | 250.0 ✓ |
| Total units | 20 | 20 ✓ |
| Sales by region | North 400, South 600 | North 400, South 600 ✓ |
| Sales by product | Notebook 500, Pen 500 | Notebook 500, Pen 500 ✓ |

### Phase D: Analysis behavior

| Check | Result | Evidence |
| --- | --- | --- |
| Worker produces actual computation | PASS | Subprocess runs pandas |
| Failed execution not narrated as success | PASS | Status returned as error/partial |
| Successful calculation survives narration outage | PASS | `status="partial"`, result preserved |
| Blank/overlong questions rejected before routing | PASS | Verified |
| Code retries bounded | PASS | `MAX_CODE_RETRIES=2` |
| Suggestions disabled by default | PASS | `ENABLE_SUGGESTIONS=False` |

### Phase E: Charts and downloads

| Check | Result | Evidence |
| --- | --- | --- |
| Chart evidence from actual plotted values | PASS | `_chart_evidence()` |
| Failed narration preserves chart | PASS | `AskResult.chart_json` populated |
| External map/image resources rejected | PASS | `_validate_chart_resources()` |
| Chart JSON bounded | PASS | `MAX_CHART_JSON_BYTES` enforced |
| Rerendering does not regenerate PNGs | PASS | Confirmed by test |
| Camera button for browser PNG | PASS | Configured in Plotly modebar |
| HTML export on request; discloses internet requirement | PASS | Verified |

### Phase F: Runner and basic security

| Check | Result | Evidence |
| --- | --- | --- |
| Parent and worker use same policy | PASS | `execution_policy.py` shared |
| Static check runs before subprocess | PASS | `check_code` executed in parent |
| Permitted imports (`pandas`, `numpy`, `plotly.*`) work | PASS | Verified |
| Unapproved/private/wildcard imports blocked | PASS | AST visitor checks |
| Print does not corrupt result channel | PASS | Captured to stdout log |
| `to_string` aliased and keyword-arg forms blocked | PASS | AST attribute check |
| Worker environment has no API keys | PASS | Minimal environment passed |
| Worker uses isolated Python mode (`-I`) | PASS | Flag passed to Python |
| Worker uses fresh temporary directory | PASS | Temp dir cleaned up |
| Timeout reaps worker | PASS | `proc.kill()` on timeout |
| Temp files cleaned after success/failure/timeout | PASS | Verified by tests |
| Parent accepts JSON only (not worker pickle) | PASS | Safe JSON parsing |
| Security doc disclaims OS sandbox | PASS | Honest documentation |
| `corr()`, `describe()`, `sort_values()`, `nlargest()` allowed | PASS | Confirmed independently |

### Phase G: Providers, configuration and errors

| Check | Result | Evidence |
| --- | --- | --- |
| `config.py` does not import Streamlit | PASS | Confirmed |
| Streamlit Secrets loaded at UI boundary | PASS | `streamlit_support.py` |
| Only allowlisted settings copied from Secrets | PASS | Filtered dictionary |
| Missing secrets file does not break `.env` setup | PASS | Handled gracefully |
| Groq SDK retries disabled (`max_retries=0`) | PASS | Tested |
| Mistral SDK retries disabled (`retry_config=None`, `retries=None`) | PASS | Tested |
| Shared request budget tested | PASS | Verified |
| Transient Groq failure falls back to Mistral | PASS | Tested in `test_providers.py` |
| Auth failure not silently switched to fallback | PASS | Tested |
| Raw provider bodies not in displayed errors | PASS | Tested |
| Dead `mistralai` fallback import (F1) | CAUTION | Identified in review |

### Phase H: Session lifecycle, privacy and display

| Check | Result | Evidence |
| --- | --- | --- |
| Uploads parsed from bytes, not saved as files | PASS | In-memory buffer |
| No active disk save/load | PASS | Verified |
| No active Gemini summarization | PASS | `summarization.txt` deleted |
| History bounded separately for turns/messages/charts | PASS | Separate bounded deques |
| Sessions do not share global DataBuddy instance | PASS | Factory function |
| Reset clears conversation/charts, keeps dataset | PASS | `ui_state.py` |
| Remove dataset clears all state | PASS | `ui_state.py` |
| CLI does not restore prior conversation | PASS | Fresh conversation object |
| `.databuddy_state` not loaded | PASS | Verified |
| Tab-close caveat disclosed | PASS | Documented in privacy guide |
| Dynamic filenames escaped | PASS | HTML escaping verified |
| `SAMPLE_ROWS=0` disclaimer present | PASS | Disclosed in docs |
| `.env`, `secrets.toml`, `uploads/`, `.databuddy_state/` gitignored | PASS | Verified |
| `.env.example` contains placeholders only | PASS | Verified |

### Phase I: Interface and terminal

| Check | Result | Evidence |
| --- | --- | --- |
| Initial page renders without keys (warning shown) | PASS | AppTest case |
| Upload help matches actual formats/limits | PASS | Matches 20 MiB CSV/XLSX |
| Dataset info updates after successful replacement | PASS | AppTest case |
| Failed replacement leaves previous dataset active | PASS | AppTest case |
| Evidence accessible from response expander | PASS | Verified |
| Terminal `/state`, `/reset`, `/quit`, empty input, EOF | PASS | `test_cli.py` |
| Terminal displays evidence on partial success | PASS | `test_cli.py` |
| Real-browser pass | NOT VERIFIED | Not performed in review-only mode |

### Phase J: Documentation and dependencies

| Check | Result | Evidence |
| --- | --- | --- |
| No stale 50 MB limit; no duplicated description | PASS | Cleaned up |
| Consistent CSV/XLSX/first-sheet documentation | PASS | Aligned across all guides |
| No claim of persisted history or Gemini summaries | PASS | Disclaimers accurate |
| Backup/checkout/previous folder distinction clear | PASS | Explicit in `README.md` |
| Core/HTTP API distinction clear | PASS | Disclaimed in `ARCHITECTURE.md` |
| Security/privacy limits agree with code | PASS | Disclaimed in `SECURITY_AND_PRIVACY.md` |
| Setup commands do not overwrite `.env` | PASS | Explicit instructions |
| Direct runtime packages pinned (9 packages) | PASS | `requirements.txt` |
| Windows snapshot not advertised as cross-platform | PASS | Disclaimed |
| Google GenAI and Kaleido not imported | PASS | Removed from active imports |
| Historical docs labeled | PASS | Moved to `docs/history/` |
| Work log records what changed, why, and what was checked | PASS | Maintained in `docs/WORK_LOG.md` |

---

## D. Independent Suggestions

**1. Remove dead `mistralai` import fallback** — `fix before demo`, small, zero cost\
Remove the `except ImportError: from mistralai.client import Mistral` branch from `llm_clients.py`. It is dead code in the pinned environment and would produce a confusing double-failure if the try-block ever failed. 1-line change.

**2. Document `uploads/` is not written by the app** — `useful now`, trivial\
One sentence in `ARCHITECTURE.md`. Eliminates contributor confusion regarding local files.

**3. Comment explaining blocked `to_string()` no-arg form** — `useful now`, trivial\
A one-line comment in `execution_policy.py` noting that `to_string` is blocked in all forms as intentional defense-in-depth, even though the no-arg form is display-only. Documents the tradeoff.

**4. Add assertion for `write_chart_insight` canned message** — `useful now`, small test\
`test_analysis.py` L156 should assert `"No numerical summary"` is in the result. Closes a minor assertion gap.

**5. Add end-to-end `explain_analysis` test without prior analysis** — `useful now`, small test\
`buddy.ask("explain that")` with no prior analysis should reach `answer_explanation`'s canned response, not raise. Currently only the routing half is tested. Small test, no code change.

**6. Whether limits are reasonable** — Yes. `EXEC_TIMEOUT_SECONDS=5` is appropriate for a 4-row demo; `REQUEST_TIMEOUT_SECONDS=75` is generous. No change needed.

**7. Whether provider calls could be reduced** — Minimally. The router always calls Mistral unless pre-checks fire. A `LOCAL_ROUTING_ONLY=true` flag would save one call per analysis question. Low priority; `later design`.

**8. Privacy wording is honest** — Yes. "Use non-sensitive demo data," "SAMPLE_ROWS=0 removes sample rows only, not all derived data," and the tab-close caveat are all appropriately hedged. No overclaiming.

**9. Docs useful to a new contributor** — Mostly yes. The `uploads/` gap (F2/suggestion 2) is the only significant omission. History docs are correctly labeled and separated.

**10. Future-design risks for a separate frontend/API** — label as `later design`:
- Session isolation: `st.session_state` is Streamlit-managed. HTTP API needs explicit session IDs.
- Code execution: worker shares host OS account. Multi-user exposure requires a real sandbox.
- RAM: 20 MiB CSV expands substantially after parsing. Free hosting (512 MB) may require a lower cap.
- CORS, rate limiting, and provider key management all become necessary at API exposure.

None are current blockers. They are the right questions when design begins.

---

## E. Final Recommendation

**Proceed with documented limitations.**

All 116 tests pass independently. The core pipeline is coherent, correctly bounded, and honestly documented. No correctness failures were reproduced.

**Before a recruiter demonstration (both are small):**
1. Remove the dead `mistralai` import fallback in `llm_clients.py` (F1 / Suggestion 1).
2. Add a sentence to `ARCHITECTURE.md` noting `uploads/` is not written by the app (F2 / Suggestion 2).

**Everything else can wait for the future design stage.**

The implementation is not over-engineered for the personal-demo scope. Tradeoffs — session-only state, Streamlit interface retained, no database, zero-budget — are correctly maintained. Stated limitations — no OS sandbox, no clean-install test, no live model test, no browser PNG test — are honestly documented.

Unverified areas (require separate owner decision): live model routing/generation quality, real-browser PNG download, clean-environment installation, Linux-host compatibility.

---

*Written in review-only mode. No application code changed. No model quota consumed. No commits, server starts, or private data uploads.*

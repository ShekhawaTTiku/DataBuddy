# DataBuddy new version: changes explained simply

Prepared on 25 October 2026. Covers the implementation and publication work recorded through 22 October 2026. This is a plain-language history of the new version, not a claim that every feature below was built from scratch.

## Where we started

The original DataBuddy already accepted datasets, answered questions, ran Python calculations, and created interactive Plotly charts. It already had a styled Streamlit web interface and a terminal interface.

The new-version work concentrated on reliability, data accuracy, temporary conversation memory, understandable failures, verification, and documentation. The original local backup remains at `D:/projects/DataBuddy`; development takes place in `D:/projects/databuddy 2.0`.

## Changes and why they matter

### 1. Protected the original version

Kept the original project as a recovery copy and worked in the new folder. Updated the working copy to the latest starting point; the incoming changes affected only the README.

**Why:** We can develop the new version while retaining an older backup.

### 2. Defined the project boundaries

Kept the project as a personal demonstration with trusted data, a 20 MiB upload limit, session-only state, and zero operating budget. Retained Streamlit and the terminal interface. Deferred a separate frontend, HTTP API, database, accounts, and persistent user storage.

**Why:** The work stays focused on a reliable demonstration without adding infrastructure or ongoing costs.

### 3. Made file loading more reliable

Standardized supported uploads around CSV and XLSX. XLSX reads the first worksheet. Removed advertised support for Excel variants that the application could not actually read. Added clearer errors for empty, malformed, oversized, or excessively large-shaped datasets. Improved text encoding handling, including UTF-8 BOM and a disclosed Latin-1 fallback.

**Why:** Users can understand why a file failed instead of seeing a confusing crash.

### 4. Kept normal uploads in memory

The upload workflow parses file bytes in the session instead of automatically saving an upload copy to disk. The local `uploads/` folder is a legacy/demo-file location, not an automatic upload destination.

**Why:** This supports temporary sessions and reduces leftover files. It does not mean data is never sent to a model provider; see the privacy guide.

### 5. Fixed dataset replacement

Files are identified by their contents as well as their names. A different file with the same name is recognized. The application changes datasets only after the replacement loads and profiles successfully. A rejected replacement leaves the last working dataset active, and rejected uploads are not repeatedly parsed during ordinary interface refreshes.

**Why:** An upload mistake no longer unnecessarily breaks a working session.

### 6. Preserved the meaning of data values

Preserved leading zeros in identifiers such as `00125`. Made date conversion conservative: clearly valid ISO date columns can convert, while ambiguous date-like text stays unchanged with an import notice. Fixed product descriptions such as `3-1/2 inch` being mistaken for dates.

**Why:** Silent type conversion should not change what the data means.

### 7. Added workload and output limits

Bounded dataset shape, dataset descriptions, questions, model context, generated code, calculation results, chart JSON, and worker output.

**Why:** A small upload can still create a large workload. Limits help keep requests and memory use manageable.

### 8. Repaired the calculation runner

Made supported imports consistent. Separated diagnostic output from returned results. Replaced worker-to-parent pickle results with checked JSON and improved invalid-result handling.

**Why:** A debug message should not corrupt a result, and the parent application should validate what the calculation process returns.

### 9. Added basic generated-code protections

Added shared code checks before execution, restricted imports and built-in functions, a minimal worker environment without provider API keys, a fresh temporary working folder, execution timeouts, and cleanup after completion or handled failure. Blocked unsupported operations, including generated `to_string()` calls because that method can also write files.

**Why:** These measures reduce avoidable execution risks for trusted demonstrations. Blocking all generated `to_string()` calls also blocks its harmless display-only form; that is an intentional tradeoff.

**Limitation:** Basic execution checks are not a hardened security sandbox. The worker still runs under the host operating-system account.

### 10. Grounded answers in real calculations

Strengthened the distinction between Python computing a result and a model explaining it. Failed execution is not presented as successful analysis.

**Why:** A convincing explanation must not hide a failed calculation.

### 11. Grounded chart explanations in plotted values

Chart narration receives evidence from actual plotted values instead of relying only on a general dataset description. Added chart-size checks and rejected unsupported external chart resources.

**Why:** The explanation should match the chart the user sees.

### 12. Preserved successful results during later failures

Save successful calculations and charts before optional narration and memory updates. If explanation or memory fails, the completed work remains available and the response can report partial success.

**Why:** One optional step should not erase useful work that already succeeded.

### 13. Improved provider failure handling

Added sanitized error messages, request and response limits, a shared deadline for each question, and bounded retries. Disabled overlapping SDK retry layers. Distinguished temporary outages from permanent credential, access, or configuration problems.

**Why:** Requests behave more predictably, and errors do not expose raw provider response bodies.

### 14. Assigned clear model roles

These are the configured defaults recorded at the verified checkpoint; account access and quotas can change.

| Job | Main model | Backup or failure behavior |
| --- | --- | --- |
| Calculation and chart code | Groq `openai/gpt-oss-120b` | Mistral `ministral-14b-latest` |
| Result narration, chart insight, optional suggestions | Groq `openai/gpt-oss-120b` | Mistral `ministral-14b-latest` |
| Conversation notes and rolling paragraph | Gemini `gemini-3.5-flash-lite` | Mistral `ministral-14b-latest` |
| Routing and ordinary chat | Mistral `ministral-8b-latest` | Local routing rules during temporary routing failures; chat failure is shown clearly |
| Explanation of previous analysis | Mistral `ministral-14b-latest` | Saved actual computation remains available |

**Why:** Each task has an explicit role and failure path. Python remains responsible for computing numerical results.

### 15. Replaced an unusable default fallback

Mistral Medium was initially chosen as the code backup. Live checks found that the tested account listed it but returned a zero request-per-minute limit. Tested Ministral 14B successfully and made it the default fallback. Environment overrides remain supported.

**Why:** A model appearing in a catalog does not prove the account can use it. No paid plan was activated.

### 16. Added working conversation summarization

The original backup kept recent turns and dropped older ones. Its Gemini-related summary function was unused. The initial cleanup removed that unused plumbing; the later owner-approved implementation added a working summary cycle for the first time.

The new cycle makes a short note after each completed exchange. At exchange six, it combines the current exchange and prior notes into one paragraph. The next six exchanges update and replace that paragraph instead of appending paragraphs forever.

**Example:** Exchanges 1–5 create notes; exchange 6 creates the paragraph. Exchanges 7–11 create new notes; exchange 12 replaces the paragraph with an updated one.

**Why:** Some older context can survive without sending an endlessly growing conversation to providers.

### 17. Bounded memory and separated it from evidence

By default, retain six recent full exchanges, up to six notes, one rolling paragraph, the last successful analysis, and up to five recent charts. Notes are limited to 400 characters each and the paragraph to 2,000 characters. Summaries are fallible context and are excluded from code-generation analysis context.

**Why:** A model-written memory should not become the source of truth for calculations. This does not guarantee recall of every old detail or filter.

### 18. Made memory failures recoverable

Gemini can fall back to Mistral. Failed updates retain the previous paragraph. Clipped local notes are marked as uncompressed, and safe notices explain limitations. Normal Streamlit refreshes do not repeat completed summary calls. Exchanges are recorded once.

**Why:** Memory failures should not discard answers or waste calls. Repeated outages can still drop older uncompressed details because storage remains bounded.

### 19. Corrected memory timing through live testing

Adjusted for Gemini's minimum ten-second API deadline. Set the default memory budget to 20 seconds inside the overall question deadline, reserve fallback time, and skip Gemini when a valid slice cannot fit. Combined the sixth exchange's briefing and paragraph update into one request.

**Why:** The earlier timing could provide too little time or require two sequential requests at rollover.

### 20. Improved the existing Streamlit interface

Retained the design while improving active-dataset information, import notices, upload controls, reset/removal behavior, and evidence expanders. Disabled input when required provider configuration is unavailable. Escaped dynamic HTML and corrected Unicode display problems.

**Why:** Users can see what is active, understand problems, and inspect supporting results.

### 21. Clarified session reset and removal

Reset clears conversation memory and charts while keeping the dataset. Removing the dataset clears its related session state. Successful replacement starts fresh related state. Sessions have separate DataBuddy instances, and the terminal does not restore legacy saved conversations.

**Why:** Controls have predictable effects and session data is not intentionally shared or persisted.

**Limitation:** Closing a browser does not guarantee immediate deletion of all server-session memory. Legacy ignored state files may still exist locally, but the current application does not load them.

### 22. Simplified chart downloads

Use Plotly's browser-side PNG download and prepare HTML exports only when requested. Removed the server-side image-export dependency on Kaleido/Chrome. Disclosed that exports contain plotted data and that HTML exports require internet access for the Plotly library.

**Why:** Downloads need fewer server dependencies and avoid repeated server image-generation work.

### 23. Improved the terminal interface

Kept `/state`, `/reset`, `/quit`, empty-input, and end-of-input workflows working. Made calculation evidence visible, including partial-success results, and added safe memory notices.

**Why:** The terminal remains a usable interface to the same core application.

### 24. Cleaned up configuration and dependencies

Moved Streamlit-specific secret loading outside core configuration and allowlisted supported secret settings. Added placeholder configuration examples. Pinned ten direct runtime dependencies and recorded the tested Windows runtime snapshot. Removed unused dependencies; Google Gen AI was later included for working memory. Retained the Mistral import compatibility path after checking the installed SDK, correcting an earlier review recommendation.

**Why:** Setup is easier to reproduce, and reusable core configuration does not require Streamlit. A fresh installation and other operating systems still require verification.

### 25. Reduced unnecessary provider calls

Disabled automatic visualization suggestions by default. Limited retries and context sizes and combined the memory rollover into one normal request.

**Why:** This conserves free quotas and avoids unnecessary work. Free-tier availability remains an external account constraint, not a guarantee of unlimited use.

### 26. Added offline automated tests

Added coverage for datasets, execution rules, calculations, charts, providers, fallback, memory, sessions, Streamlit, terminal behavior, and a synthetic demo. Tests use fake provider responses and block external network connections in the parent process; they do not call live providers or consume API quota.

**Recorded result:** The latest pre-publication run on 22 October passed 152 tests. Dependency consistency and other recorded checks also passed. This historical result is separate from any checks performed when preparing this document.

**Why:** Changes can be checked repeatedly without using provider quota.

### 27. Completed independent review and live verification

Prepared an Antigravity review handoff and retained its report, with later corrections clearly attributed. Tested real provider calls against the supplied Superstore dataset and checked results against independent aggregates. Completed twelve exchanges, including two memory rollovers and older-preference recall. Checked browser upload, chart values and narration, PNG/HTML downloads, reset, removal, and corrected replacement upload.

**Why:** Offline tests cannot establish real account access, provider timing, or browser download behavior. Reports retain aggregate evidence rather than private dataset rows or raw conversations.

### 28. Rebuilt current documentation

Updated setup, architecture, privacy, provider/memory behavior, demo instructions, implementation records, validation, live verification, and recovery guidance. Moved superseded material into labeled history and added project instructions for maintaining documentation.

**Why:** Current guides should describe actual behavior and distinguish completed work from future ideas.

### 29. Published a private recovery checkpoint

After owner authorization, published the verified version to the private `ShekhawaTTiku/DataBuddynew` repository in five groups: core safeguards; providers/memory; interfaces; tests/tools; and documentation/evidence. Preserved existing history. Kept credentials, private datasets, legacy saved state, caches, and temporary files out of version control. The original repository remains an upstream reference.

**Why:** The new version has a recoverable remote checkpoint. Publication did not deploy the application or introduce paid services.

## Remaining boundaries

- Basic execution protections are not a hardened security sandbox for public or untrusted multi-user use.
- Summaries can forget or misstate details; actual computed evidence remains separate.
- Provider availability, free quotas, and response times depend on external accounts and services.
- Session-only storage does not guarantee immediate cleanup when a browser closes, and provider calls can transmit bounded data-derived context.
- Clean-environment installation and Linux-host compatibility were not verified in the recorded checkpoint.
- A replacement frontend, API, database, accounts, persistence, and new deployment remain outside the completed work.

## Detailed records

- [Work log](WORK_LOG.md): stages, reasons, corrections, and checks.
- [Implementation plan](IMPLEMENTATION_PLAN.md): agreed work packages.
- [Providers and memory](PROVIDERS_AND_MEMORY.md): model roles, lifecycle, and limits.
- [Security and privacy](SECURITY_AND_PRIVACY.md): disclosures and execution limitations.
- [Validation](VALIDATION.md): recorded automated checks.
- [Live verification](LIVE_VERIFICATION.md): real-provider and browser results.
- [GitHub checkpoint](GITHUB_CHECKPOINT.md): destination, publication groups, and exclusions.

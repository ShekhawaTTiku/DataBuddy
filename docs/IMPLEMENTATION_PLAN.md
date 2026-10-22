# Scope and implementation plan

## Agreed purpose

A personal portfolio showcase for the owner, friends and recruiters, with trusted ordinary demo data and zero operating budget. The existing app must work reliably and match its documentation before a future frontend is designed. No new web app, HTTP API, database, accounts, persistent user storage, paid services or deployment.

## Work packages and implementation

| # | Agreed change | Implementation |
| --- | --- | --- |
| 1 | Synchronize baseline | Fast-forwarded README-only upstream changes; local fixes branch, no new commits/pushes |
| 2 | 20 MB upload | Fixed 20 MiB limit in Streamlit and Python loaders; CSV primary, XLSX first sheet |
| 3 | Replacement correctness | Content fingerprint; state switches only after successful load/profile |
| 4 | File errors | Clear format, empty, malformed, size and shape errors; rejected uploads not reparsed on rerun |
| 5 | Date accuracy | Whole-column valid ISO conversion only; other date-like text preserved with notices |
| 6 | Runner reliability | Separate bounded diagnostic output, validated JSON, consistent permitted imports |
| 7 | Basic safety | Shared AST checks, restricted builtins, isolated temp cwd, minimal env, timeout and cleanup |
| 8 | Output limits | Bounded prompts, questions, profile, results, code, chart JSON and worker pipes |
| 9 | Chart grounding | Narrative receives bounded actual plotted evidence rather than guessing from a profile |
| 10 | Partial success | Calculation/chart retained when optional narration fails |
| 11 | Session-only memory | In-memory conversation, recent-turn/chart limits; owner-approved Gemini six-note/rolling-paragraph memory added on 2026-10-22, with Mistral fallback; no persistence |
| 12 | Reset/cleanup | Explicit clear controls; upload bytes stay in memory; runner files removed on completion/timeout |
| 13 | Provider reliability | Safe error messages, timeouts, shared elapsed budget, single retry layer and bounded tokens |
| 14 | Text display | Escaped dynamic HTML; ordinary text/dataframe for column information |
| 15 | Exports | Browser-native PNG and HTML prepared only on request; no Kaleido/Chrome server dependency |
| 16 | Small usability fixes | Visible active dataset, import notes, disabled unconfigured input, evidence expander |
| 17 | Configuration/dependencies | UI-specific secret bootstrap, allowlisted settings, placeholder example, pinned dependencies |
| 18 | Verification/docs | Offline regression suite, synthetic demo, focused guides and final validation record |

## Decisions and limits

- Keep existing theme/layout; changes serve reliability, not visual redesign.
- The core accepts bytes/streams/path plus filename and returns AskResult, suitable for a later API wrapper. An API itself is deferred.
- Keep functional XLSX support; remove unsupported Excel formats rather than install more readers.
- Server-side image rendering remains removed. Unused Gemini plumbing was removed during the initial cleanup, then reintroduced as a working memory feature at the owner's request on 2026-10-22. Free quotas remain external account constraints.
- Execution is basic trusted-demo protection, not public multi-user isolation. Do not describe it as a secure sandbox.
- Closing a browser does not synchronously notify every server component. No durable upload/history is created; explicit removal clears active state, and disconnected session memory is eventually released by Streamlit.

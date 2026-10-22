# Private GitHub checkpoint

Date: 2026-10-22, Asia/Kolkata. The owner explicitly authorized committing and pushing the verified working version in logical batches to the newly created private [ShekhawaTTiku/DataBuddynew](https://github.com/ShekhawaTTiku/DataBuddynew) repository.

## Destination and history

- Working checkout: `D:/projects/databuddy 2.0`.
- Destination: `https://github.com/ShekhawaTTiku/DataBuddynew.git`, branch `main`.
- Before the first push, GitHub authenticated metadata confirmed this exact repository was private and empty.
- The working copy's `origin` now names DataBuddynew. The old DataBuddy repository is retained as `upstream`, for reference; no push targets it.
- The original project history is retained. Before publication, 44 historical Git blobs and 71 current candidate files were scanned for configured keys and recognizable credential formats. No matches or private dataset/state files were found. One checkpoint document is added during publication.
- Local branch `codex/demo-stability-fixes` publishes explicitly to `origin/main`. Future publishing commands must specify the intended destination; no force push, tags or other branches are part of this checkpoint.

## Publication batches

The first push also transfers the existing audited project history. Each numbered batch is a separate commit and separate push, checked against the remote branch immediately afterward. Individual intermediate commits group related work; the final combined checkpoint is the runnable, fully verified application.

| Batch | Content | Commit |
| --- | --- | --- |
| 1 | Ignore rules, project guidance, dataset ingestion and basic execution safeguards | `eaa8eb5` |
| 2 | Configuration/dependencies, providers, memory, analysis pipeline and prompts | `3b2bf85` |
| 3 | Streamlit/terminal interfaces, session helpers and UI secret bootstrap | `a24ade6` |
| 4 | Offline tests, synthetic example and explicitly opt-in live verification tool | `20d55ad` |
| 5 | README, current/historical guides, validation, aggregate verification evidence and this checkpoint record | Commit titled `docs: record verified demo and private GitHub checkpoint` |

The documentation commit completes the checkpoint. Its own hash is available from GitHub's `main` branch/commit history; it cannot be included inside its own contents without changing that hash.

## Files that stay local

- `.env` and other real environment settings; only the placeholder `.env.example` is versioned.
- `.streamlit/secrets.toml` and actual provider credentials.
- `uploads/`, including the supplied private Superstore CSV and any future datasets.
- `.databuddy_state/` and legacy saved state.
- Virtual environments, Python caches, test caches and coverage output.
- Downloads and temporary worker files.

The only versioned CSV is `examples/demo_sales.csv`, the four-row synthetic fixture. Documentation includes aggregate-only checks, a chart and an app screenshot with the dataset preview collapsed; no source dataset rows, raw conversations or provider response bodies are included. Private-repository status is an additional access control, not permission to commit credentials.

## Verification and original backup

- Fresh pre-publication suite: **152 passed in 31.69 seconds**, entirely offline; dependency consistency passed. Existing live verification is documented separately in [LIVE_VERIFICATION.md](LIVE_VERIFICATION.md); no extra live model calls are necessary for publication.
- Before every commit, the staged file list and contents are checked for excluded paths/configured keys and whitespace errors. Final verification compares local/remote commit and tree identities, checks GitHub privacy and file paths, and confirms a clean local index/worktree.
- The original `D:/projects/DataBuddy` backup is not edited. Its checkout remains at `8d3b78a`; its tracked status and private `.env`/CSV identities are checked separately.
- API keys and local-only datasets are intentionally absent from GitHub. A future clone must use its own private credentials and the synthetic example or a locally supplied dataset.
- To recover this complete working version later, select the final documentation checkpoint (or a later known-good complete commit) from `main` in DataBuddynew. Restore into a separate folder first so subsequent uncommitted work is not overwritten. The original local backup remains a second recovery copy.

No GitHub Actions workflow, public deployment, replacement frontend or paid service is introduced by this publication. Earlier no-push statements in implementation/live records describe their historical stages, before the owner authorized this checkpoint.

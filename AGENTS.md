# DataBuddy project instructions

- Work in this checkout only. D:/projects/DataBuddy is the original local backup; do not edit it.
- Purpose: trusted personal demo, maximum 20 MiB upload, session-only state, zero operating budget. No new frontend/API/database/accounts unless the user changes scope.
- Maintain current documentation under docs/. Record steps, reasons, checks and material limitations in docs/WORK_LOG.md; update focused guides when behavior changes.
- Do not expose keys, private dataset rows, saved conversation contents or raw provider response bodies in docs/logs.
- Run python -m pytest -q and relevant checks after meaningful changes. Tests must not call live providers or consume API quota.
- Basic execution checks are not a hardened security sandbox. Keep that limitation explicit.
- Do not commit, push or deploy unless explicitly authorized by the user.

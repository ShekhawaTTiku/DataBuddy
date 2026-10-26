# DataBuddy interface preview

Date: 2026-10-26. Source: [interactive fragment](databuddy-preview.html). Design requirements: [accepted brief](../WEBAPP_DESIGN_BRIEF.md).

This is a visual, interactive mockup shown in the project conversation, not a frontend/API integration or deployed service. It uses only synthetic rows, predetermined answers and illustrative usage figures. It does not read private uploads, call providers, count tokens accurately, enforce real quotas or create persistent chat history.

## Review flow

1. Start at Welcome. Use Try sample data, select a task, then Send. The brief running state and sample answer demonstrate the interaction only.
2. Open the result preview; switch among Chart, Result data and Calculation. Open dataset overview from the sidebar.
3. Switch theme using the sidebar footer. At phone widths, open the sidebar drawer first.
4. Hover/focus Usage for details; click/tap to pin the card. The red input-warning information control explains the separate allowance feedback.
5. Use the conversation preview's design controls to select Welcome, Sample loaded, Conversation, Analysis, High input, Adjusted allowance, Allowance reached, Partial success or Running. Choose Desktop/Mobile and Light/Dark; the accent and composer-corner controls support later design experiments. A standalone inspection wrapper without host design controls receives simple screen/width selectors instead.
6. Reset and remove use confirmation dialogs. They preserve the mock session's allowance. Allowance reached retains access to existing results.

The app-style surface is labelled Portfolio demo; the surrounding caption explicitly identifies a design preview. Upload selection is represented by a sample-data dialog. Export actions demonstrate their placement/disclosure and explicitly produce no files. Chat shows a representative latest exchange, not a complete message-history implementation. The typed-input counter uses a deliberately rough preview-only heuristic; the High input scene uses an illustrative count. The 1,200-token figure and usage examples are not calibrated policy thresholds or account observations.

## Verification

- Fragment under 1 MB; embedded JavaScript passed Node syntax validation.
- Browser walkthrough: sample entry, task prompt, submit, result, panel, data/calculation tabs, dark theme, usage card, reset retention, adjusted/exhausted allowances and partial success.
- Four core scenes checked at viewport widths 320, 390, 736 and 1024 pixels without horizontal overflow in the app/root. Actual inner widths differ because the inspection wrapper adds margins. Phone navigation and full-screen analysis view inspected visually.
- No browser console errors observed during these checks. Rich host design controls were not available in the standalone inspection wrapper; their bindings were reviewed, while browser testing used the fallback selectors.
- Existing offline regression suite: **152 passed in 41.71 seconds**. No live provider requests or quota consumed.

Remaining work: owner visual review, production accessibility/contrast checks, final typography/palette refinements, usage-policy calibration, framework/API selection and implementation. This mockup is not proof of security or hosting feasibility; existing basic execution safeguards are not a hardened security sandbox. No commit, push or deployment was performed.

# Dedicated web app: accepted design direction

Updated 2026-10-27. The owner authorized the complete implementation and refined the UI to remove text clutter and decorative quotes. This document records the accepted design; [working setup](WEBAPP_SETUP.md), [design notes](WEBAPP_DESIGN_NOTES.md) and [verification](WEBAPP_VERIFICATION.md) describe the implemented behavior. The earlier mockup is a historical design artifact, not the application. Render runtime feasibility remains conditional.

## Purpose and boundaries

Build DataBuddy's dedicated portfolio web experience around the verified Python core. Use Claude's web chat as the interaction reference, with DataBuddy branding and data-analysis workflows. Preserve zero operating budget, trusted demo data, the 20 MiB upload cap, session-only state and no accounts/database. Keep the original backup untouched. Basic execution checks are not a hardened security sandbox.

## Visual design

- Start with warm ivory `#F7F6F2`, light-stone sidebar `#ECEBE5`, white surfaces `#FFFFFF`, charcoal text `#252824` and muted teal accent `#26736B`. Define central theme values so later palette experiments are straightforward. Check contrast in the mockup; these colors are a starting direction, not a contrast certification.
- Support light and dark modes, with light initially selected. Derive a coordinated dark palette during mockup work.
- Restrained serif welcome heading; clean sans-serif messages, controls and tables. Exact fonts remain to be selected.
- Collapsible left sidebar, spacious central conversation and an on-demand right analysis panel. Let chat use available space while the panel is closed.
- Subtle transitions and hover/focus states. Preserve usability with reduced motion and touch interaction.
- Mobile: sidebar drawer and full-screen analysis view, with chat as the main screen.

## Interface and behavior

| Area | Accepted direction |
| --- | --- |
| Sidebar | DataBuddy branding, active dataset/details, reset conversation, remove dataset, theme toggle and About link. Session-only memory; no persistent saved-chat history. Multiple concurrent conversations are not an accepted requirement. |
| Welcome | Short instruction: "Start with your data" and "Upload a spreadsheet, then ask a question." Upload/sample actions and task buttons. |
| Task buttons | Explore my data; Create a chart; Compare groups; Find trends; Check data quality. Keep Try sample data prominent. Guide to upload/sample first when no dataset exists. Selecting a task does not automatically trigger paid/quota-consuming generation. |
| Composer | Rounded multiline input, attachment/send actions, active filename, Enter to send and Shift+Enter for newline. Prevent duplicate submission while busy. |
| Answers | Readable text, compact tables and appropriate key figures; View calculation, View result data and Copy answer actions. |
| Analysis panel | Chart previews open a larger panel with Chart, Result data and Calculation views, dataset preview and existing PNG/HTML exports. |
| Progress/errors | Report actual backend stages when available; preserve computed results/charts if narration fails; show appropriate error/retry feedback. Do not invent progress or report success before execution finishes. |
| Follow-ups | Relevant suggestions derived locally from dataset columns/types initially; avoid extra provider calls merely to populate the interface. |

## Session allowance and high-usage feedback

1. Start each session with an application allowance of 15 messages. This is an app policy, not a provider guarantee or account-level per-person entitlement.
2. Estimate input tokens internally as the user types. Above the agreed baseline, show a red notice below the composer with the estimated token count and an information icon. Mark estimates as approximate and model-specific.
3. The notice explains that consistently high token usage may reduce the session's remaining message allowance. It can appear for the first message, before usage-based adjustment occurs.
4. After the first 2-3 completed exchanges, compare observed average whole-exchange usage with the calibrated baseline. High usage can reduce total session allowance by 1-2 messages, with explicit feedback and an updated remaining count.
5. Example only: after three messages, 12 normally remain from 15; reducing the total allowance to 13 or 14 leaves 10 or 11. This changes message count, not the model's per-response token cap.
6. Accepted refinement: use the typed-message estimate for immediate feedback, but use whole-exchange usage for allowance decisions. Account for routing, code generation, narration, memory and observed retries/fallbacks; short visible questions can still cause substantial usage.
7. Avoid repeatedly deducting for the same high-usage observations. Never display a negative remaining count or retrospectively invalidate a completed answer.
8. This policy belongs in the backend as well as the display. Resetting conversation memory must not accidentally reset the usage budget; exact reset/new-session rules are still to be settled.

Implemented policy and offline calibration are documented in WEBAPP_SETUP.md: 600-token approximate input warning; 12,000-token planning baseline; one complete-metadata review after three accepted submissions; validation/capacity rejections do not count; accepted failures count. These are application thresholds, not live provider averages or quota guarantees.

## Separate detailed Usage control

A discreet Usage icon opens a small detailed card on hover/focus, can be pinned by click and works by tap on mobile. Use subtle motion and respect reduced-motion settings. The high-input notice and this control serve separate purposes.

Show only the metadata or calculations actually supported:

- Provider-reported input/output/total tokens for completed calls; expose reasoning/cache categories separately if supplied rather than treating visible text as all usage.
- Per-exchange and session totals, broken down by provider/model, with recorded attempts and fallback activity.
- Current application allowance, remaining messages and any usage-related adjustment.
- Provider-reported remaining requests/tokens, applicable time window, reset/retry time and last-update time where available.
- Clear Estimated, Reported, Observed or Unavailable labels. Failed/time-limited requests can lack usage even if a provider did work; incomplete observations are not exact billing or account totals.

Groq documents token usage and remaining daily-request/per-minute-token headers. Gemini returns usage metadata and applies quotas at project level. Mistral returns usage metadata and applies shared organization limits; validate usable headers before promising remaining-quota values. Shared account usage and changing quotas prevent a guaranteed number of future user questions. Do not add unlike provider quotas into a single remaining-token balance. Opening the card reads collected metadata rather than triggering another generation request.

Provider functions now record allowlisted usage metadata in a request-local observer while retaining their text-return interface. Counters stay in session memory. Groq quota headers are collected when returned; unsupported metadata remains unavailable. No raw prompt/response logging is added.

References reviewed during discussion: [Groq usage](https://console.groq.com/docs/api-reference), [Groq rate limits](https://console.groq.com/docs/rate-limits), [Gemini token counting](https://ai.google.dev/api/tokens), [Gemini limits](https://ai.google.dev/gemini-api/docs/rate-limits), [Mistral responses](https://docs.mistral.ai/api/endpoint/chat), [Mistral limits](https://help.mistral.ai/en/articles/698531-why-am-i-hitting-api-rate-limits-and-how-do-i-increase-them). No fresh account-quota inspection or inference calls were made.

## Next step

Deploy when authorized using WEBAPP_SETUP.md. Local UI/API implementation and offline verification are complete. Actual Linux container execution, Render resource/cold-start acceptance and deployment-origin checks remain part of deployment. Commit, push and deployment remain separately authorized actions.

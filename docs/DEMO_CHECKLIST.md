# Repeatable demo checklist

Use examples/demo_sales.csv, a synthetic four-row dataset containing no private information. The automated suite tests calculations against known answers without model calls; live wording/routing still depends on provider access and responses.

## Expected answers

| Question | Expected evidence |
| --- | --- |
| Total sales | 1000 |
| Average sales | 250 |
| Total units | 20 |
| Sales by region | North 400, South 600 |
| Highest-sales product | Notebook 500 and Pen 500: a tie, not one clear winner |
| Sales by month | January 300, February 700 |
| Missing sales values | 0 |
| Bar chart of sales by region | North 400, South 600; explanation uses actual plotted evidence |

## Demonstration flow

1. Install/configure according to SETUP.md. Upload the synthetic CSV and inspect the four-row preview.
2. Ask a calculation, then a follow-up, then request a chart and change its title/orientation.
3. Expand computed evidence and calculation; compare with the table above.
4. Download PNG with the camera button. Prepare interactive HTML only if needed; it uses the internet and contains chart data.
5. Reset conversation: dataset remains, old chart/follow-up context, summary and notes disappear.
6. Replace a CSV with changed contents under the same filename: preview/results update.
7. Select a broken/empty CSV: clear error, previous dataset remains active.
8. Remove dataset and clear session: preview/history disappear and uploader resets.
9. In a new session/run, confirm there is no restored dataset or conversation.

## Failure checks

Automated tests cover narration outages preserving results, provider quota/authentication errors, rejected file/network code, timeouts, output limits and rejected uploads not being reparsed. Memory tests cover six-note rollover, old-paragraph merging, Mistral fallback, bounded repeated failures, session reset and safe UI/CLI notices. Do not intentionally burn free API quota to test failures; use the offline suite.

For a live memory check with available free quota: complete six exchanges, inspect `/state` in the CLI (the older paragraph should exist), then complete six more and confirm it is replaced by a merged paragraph. Confirm specific corrections and preferences survive; do not treat remembered numbers as a replacement for a fresh calculation. Reset and confirm the paragraph/notes disappear. The owner-authorized Superstore run completed this acceptance check on 2026-10-22; see [LIVE_VERIFICATION.md](LIVE_VERIFICATION.md). Automated pytest tests remain offline.

The real private uploads/Superstore.csv was also checked locally for loading and deterministic aggregates; it is not included in Git. It is not required to run the synthetic demonstration.

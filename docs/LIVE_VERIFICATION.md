# Superstore live acceptance verification

Date: 2026-10-22, Asia/Kolkata. Working checkout: `D:/projects/databuddy 2.0`. The owner supplied `uploads/Superstore.csv` and explicitly requested completion of real-provider verification. These checks used actual provider API quota; the ordinary pytest suite remains offline.

**Outcome: the final configured trusted-demo workflow passed the live acceptance checks.** Two memory timing defects and a misleading import warning were corrected. The initially selected Mistral Medium model has zero request-per-minute allowance on this account; the final code fallback defaults to working Ministral 14B. No paid plan, billing setting, deployment, new frontend, commit or push was created.

## Dataset and independent expected values

The supplied CSV is 2,287,806 bytes, 9,994 rows and 21 columns. Its Latin-1 encoding is handled with an import notice; leading-zero Postal Code values remain text. Ambiguous Order Date/Ship Date strings remain unchanged rather than being guessed. The loader no longer mistakes product dimensions such as `3-1/2 inch` for dates. No raw rows, customer records, full model answers, generated code, credentials or conversation summaries are included in these reports.

| Deterministic check | Expected result |
| --- | --- |
| Total Sales | 2,297,200.86 |
| Total Profit | 286,397.02 |
| Row count | 9,994 |
| Central Sales | 501,239.89 |
| East Sales | 678,781.24 |
| South Sales | 391,721.91 |
| West Sales / highest region | 725,457.82 / West |

All expected results were computed independently from the loaded DataFrame before comparing model-generated execution evidence. Monetary comparisons use a 0.02 tolerance, average Discount a 0.000001 tolerance, and counts exact equality. Chart checks decode Plotly typed arrays and compare every regional value, rather than checking only that a figure exists.

## Twelve-exchange acceptance run

All twelve checks passed with success status and no memory notice in the completed run:

1. Remember an explicit teal chart-color preference.
2. Calculate total Sales across all rows.
3. Explain the previous calculation.
4. Identify the highest-sales Region and its total.
5. Create a regional Sales bar chart; compare actual plotted values.
6. Change only the chart title. First memory rollover: one 881-character paragraph, zero pending notes, teal preference retained.
7. Calculate total Profit across all rows.
8. Count all rows.
9. Calculate Sales for each Category and compare all category aggregates.
10. Calculate average Discount with sufficient precision.
11. Count missing Sales values.
12. Recall the teal preference after it has left the six-full-exchange window. Second rollover: one replacement 994-character paragraph, zero notes, preference retained.

Six recent full exchanges remained bounded throughout. Reset cleared notes, paragraph, full exchanges, chart history and last analysis. Dataset replacement created fresh memory, and a separate DataBuddy instance started empty.

Observed question times were 11.81–22.52 seconds in the completed paced run. Provider metadata records 18 successful Groq operations; 12 Gemini operations, of which six completed directly and six reached the bounded time limit; and 17 successful Mistral operations including ordinary routing/explanation and memory fallback. These are application-level operations, not an exact billable HTTP-attempt count. Both default-budget rollover requests used Mistral fallback successfully. A separate native Gemini compression request with synthetic aggregate notes passed in 12.48 seconds, retaining the preference; that diagnostic used a 30-second overall budget and the existing 20-second per-attempt cap. The app's memory budget remains 20 seconds. This demonstrates working primary and fallback paths without claiming every summary is always produced by Gemini.

Raw aggregate-only machine results: [completed twelve-exchange run](LIVE_VERIFICATION_RESULTS.json), [native Gemini compression](LIVE_GEMINI_COMPRESSION_RESULTS.json).

## Live fallback verification and final model choice

All selected model IDs appeared in provider catalogs, but catalog listing alone did not prove inference allowance. A real Mistral Medium request returned HTTP 429; a later minimal request confirmed `x-ratelimit-limit-req-minute: 0` and remaining requests zero. Waiting between normal requests cannot create allowance where the account advertises zero. No account limit or payment setting was changed. Official guidance confirms limits are model/account specific: [Mistral API limits](https://help.mistral.ai/en/articles/698531-why-am-i-hitting-api-rate-limits-and-how-do-i-increase-them).

Ministral 14B passed actual calculation-code generation, chart-code generation, narration and memory requests. The default `MISTRAL_FALLBACK_MODEL` is now `ministral-14b-latest`; an explicit environment override can still select a different accessible model later. The existing private `.env` was not edited.

Final configuration:

| Role | Primary | Fallback |
| --- | --- | --- |
| Code and chart code | Groq GPT-OSS 120B | Ministral 14B |
| Result/chart narration | Groq GPT-OSS 120B | Ministral 14B |
| Conversation notes and paragraph | Gemini 3.5 Flash-Lite | Ministral 14B |
| Routing / ordinary conversation | Ministral 8B | Local routing during outages / clear chat error |
| Explain prior analysis | Ministral 14B | Saved computed evidence |

Tests temporarily omitted primary credentials **inside isolated verification processes only**, preserving all saved credentials. A final full `DataBuddy.ask` chart request with Groq omitted succeeded through the final fallback configuration: plotted values exactly matched the regional aggregates, narration succeeded, a memory note was created and no memory notice appeared. This took 23.72 seconds.

Evidence: [initial fallback probes](LIVE_FALLBACK_RESULTS.json) preserve the Medium failure and successful narration/memory fallback; [working 14B code/chart probes](LIVE_CODE_FALLBACK_RESULTS.json); [final full fallback pipeline](LIVE_FINAL_CONFIG_RESULTS.json). The twelve-exchange report records Medium as its then-configured code fallback, although all Groq operations in that run succeeded. The later final-configuration test verifies the replacement 14B default; the historical metadata was not rewritten to imply that the earlier run used a different configuration.

## Browser verification

Used the actual Streamlit app on loopback `127.0.0.1:18501` with the supplied CSV:

- Uploaded the file through the browser file chooser; 9,994 rows / 21 columns / zero missing values appeared.
- Submitted a real regional Sales chart question. The chart rendered with correct values and evidence-based narration.
- Downloaded a valid PNG, 2400 by 1200 pixels: [verified chart export](verification/Superstore-chart.png).
- Prepared and downloaded interactive HTML (9,654 bytes). Confirmed Plotly/CDN content and the on-page disclosure that HTML contains plotted data and needs internet.
- Reset conversation: history/chart disappeared while dataset stayed loaded.
- Removed the dataset: the welcome/upload state returned.
- Reuploaded after the loader fix: the product-name date warning disappeared; genuine date/encoding/Postal Code notices remained. Preview stayed collapsed so screenshots contain no dataset rows.
- Captured the corrected loaded state: [browser verification screenshot](verification/Superstore-ready.png).

The temporary browser tab and verification server are cleaned up after verification. Downloaded PNG/HTML remain in the user's Downloads folder; the aggregate-only PNG evidence is also under docs/verification. No public URL or deployment was created.

## Defects found and fixes

1. **Invalid Gemini deadline:** the old 10-second memory budget reserved 40% for fallback, leaving six seconds for Gemini. The real API rejects deadlines below ten seconds. The default memory budget is now 20 seconds; Gemini receives its minimum valid slice when it fits. If it cannot fit, the app skips Gemini and uses Mistral without exceeding the overall deadline.
2. **Rollover used two sequential memory requests:** briefing exchange six and then merging could exhaust the memory budget. The sixth exchange is now briefed and merged with five notes/the older paragraph in one request. Normal operation uses one memory request per exchange, including rollover. Failure still preserves the prior paragraph and at most six clipped local notes.
3. **Irrelevant product date notice:** date-like text matching accepted arbitrary trailing product descriptions. It now accepts only a date-shaped value with an optional time suffix, preserving mixed/ambiguous real date columns and avoiding the false product warning.
4. **Unavailable Medium fallback:** account model listing hid zero inference allowance. Selected the already-verified 14B alternative for the zero-budget code fallback. No paid upgrade or extra fallback cascade was added.

The SDK's automatic function calling is explicitly disabled for the memory-only text task, and the supported Flash-Lite models use minimal thinking without custom sampling temperature. Official thinking guidance: [Gemini thinking levels](https://ai.google.dev/gemini-api/docs/thinking).

## Final checks and remaining limits

- Final offline suite: **152 passed in 32.05 seconds**, including new deadline, combined rollover and product-dimension regressions. No live calls occur in pytest.
- Dependency consistency passed; all ten direct runtime pins match installed versions. No install/upgrade was performed.
- Saved `.env` and supplied Superstore CSV hashes match their original backup counterparts. Original checkout is not edited. Final syntax, whitespace, documentation-link, exact configured-key and Git checks are recorded in VALIDATION.md.
- Live-run helper: `python scripts/verify_live_demo.py --live`, from the project root. Without `--live`, argument validation exits before importing the provider/application modules. Default pacing is 40 seconds between Groq-heavy questions. Running it uses provider quota and replaces the latest live-results JSON; it does not run automatically as part of the app or offline tests.
- Earlier diagnostic attempts are preserved as [initial deadline failure](LIVE_VERIFICATION_INITIAL.json) and [two-request rollover failure](LIVE_VERIFICATION_BUDGET_RETRY.json). They were intentionally stopped before completing twelve exchanges; they are diagnostic evidence, not passing acceptance runs.
- This is a finite acceptance sample, not proof of universal model correctness, guaranteed provider uptime/latency or free hosting capacity. Summaries can omit details; generated answers must remain tied to computed evidence. Native Gemini can be slower than its allotted primary slice, so Mistral fallback is operationally important.
- Clean-environment installation, Linux/mobile responsiveness, long concurrent load, billing/account configuration and hardened public execution isolation were not verified. The app remains a trusted personal demonstration with basic safeguards and session-only storage. Browser close is not an immediate server-memory deletion guarantee.

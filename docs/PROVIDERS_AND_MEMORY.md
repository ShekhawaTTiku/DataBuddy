# Providers and temporary conversation memory

The dedicated API captures allowlisted usage metadata and available Groq quota headers. As of 2026-10-30, web chat/narration also delivers incremental text through request-local callbacks while preserving the completed string-return interface. Routing, code generation and memory remain buffered. Web routing is classification-only followed by a separate streamed Mistral chat call; legacy interfaces retain combined router/chat behavior. See [streaming](STREAMING.md) and [usage policy](WEBAPP_SETUP.md) for recovery, estimates, reported totals and unavailable account quotas.

Implemented at the owner's request on 2026-10-22 (Asia/Kolkata). This supersedes the initial readiness decision to omit active Gemini summarization. The original backup already used a rolling recent-turn window; it contained an unused Gemini function, not a working summary cycle. Removing that unused plumbing did not remove an active feature. This implementation adds the agreed cycle for the first time in the working checkout.

## Model roles

| Task | Primary | Fallback |
| --- | --- | --- |
| Analysis and chart code | Groq `openai/gpt-oss-120b` | Mistral `ministral-14b-latest` |
| Computed-result narration, chart insight, optional suggestion | Groq `openai/gpt-oss-120b` | Mistral `ministral-14b-latest` |
| Brief notes and rolling paragraph | Gemini `gemini-3.5-flash-lite` | Mistral `ministral-14b-latest` |
| Routing and ordinary chat | Mistral `ministral-8b-latest` | Local routing rules during outages; chat failure is shown clearly |
| Explain previous analysis | Mistral `ministral-14b-latest` | Saved actual computation remains available |

Python computes the result; providers generate code, interpret evidence or maintain fallible conversation context. A model-written summary never replaces actual evidence. Small role-specific models avoid using the largest model for every task. Model availability was checked live on the owner's account: Medium appeared in the catalog but returned HTTP 429 with a zero request-per-minute limit. The default code fallback therefore uses Ministral 14B, which passed actual Superstore calculation/chart code generation, narration and memory checks. This respects the zero-budget scope; no paid plan was activated. Existing model environment overrides are respected.

Official references checked on 2026-10-22: [Groq supported models](https://console.groq.com/docs/models), [Gemini Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), [Mistral model IDs](https://docs.mistral.ai/vibe/code/cli/configuration), [Google Gen AI SDK](https://googleapis.github.io/python-genai/), [Gemini pricing/free-tier disclosure](https://ai.google.dev/gemini-api/docs/pricing). No billing, paid plan or account settings were activated or inspected; quotas/access depend on the owner's accounts. Ordinary free-tier text inference is used without tools, search, caching or server-side Gemini conversation storage.

The Mistral SDK import compatibility fallback remains: try `mistralai.Mistral`, then `mistralai.client.Mistral`. The latter works with installed SDK 2.10.1, so the Antigravity suggestion to delete it was not adopted.

## Six-note cycle

1. Finish the answer and preserve any computed result/chart. The web app can display verified evidence and progressively generated text before finalization. Record exactly one exchange in recent history, including an explicitly stopped/partial status when appropriate; never record individual chunks.
2. Request one brief plain-text note about that exchange. The bounded payload includes question, answer, computed result text if present and success/partial/error status. No separate DataFrame, raw profile or code is supplied to the memory engine.
3. Keep up to six notes, each at most 400 characters.
4. At the sixth exchange, brief the new exchange and merge it with the five previous notes and previous rolling paragraph, if any, in ONE provider request. Return one new paragraph of at most 2,000 characters. Replace the paragraph and clear the slots only after successful compression. This preserves the six-exchange cycle while avoiding two sequential requests at rollover.
5. Fill the next six slots one by one and repeat. Do not append old paragraphs indefinitely.
6. Independently keep the latest six full exchanges by default (configurable), last successful analysis and up to five charts. Summary and notes are included as untrusted context for routing/chat/answer writing, within the global context limit. Code-generation analysis context uses recent analysis and saved actual evidence rather than summary claims or casual facts. Older summarized details therefore help conversation continuity but do not guarantee arbitrary old calculation/filter recall.

Example: exchanges 1–5 produce five notes; exchange 6 produces a paragraph and clears notes; exchanges 7–11 produce five new notes alongside that paragraph; exchange 12 replaces the paragraph with a merged version and clears notes again.

All fields belong to one `ConversationState`, held by its session's `DataBuddy`, which can exist before a dataset is loaded. No database, files, shared cache or background job stores this memory. Reset clears all memory fields. The first successful upload preserves introductory chat and memory. Replacing an existing dataset or removing it clears chat and memory. Browser disconnection/close is not an immediate server-memory deletion guarantee.

## Failure and call limits

- Missing Groq/Gemini credentials permit direct Mistral fallback when configured. Temporary outages, connection timeouts, 408/429 and 5xx failures permit fallback after the bounded retry policy. Empty primary responses also permit fallback. Invalid credentials, access denials and unsupported model/request errors are configuration failures and are reported without silent provider switching.
- Routing uses local rules during temporary Mistral failure or malformed routing output. Permanent Mistral configuration failures surface clearly. Mistral cannot fall back to itself.
- SDK retry layers are disabled. The shared question deadline includes routing, code, narration and memory. Where Mistral is configured, primary calls normally receive 60% of remaining role-call time, reserving time for fallback. Gemini requires a minimum 10-second API deadline, discovered during live verification: its slice is raised to 10.1 seconds when enough total time remains, otherwise Gemini is skipped for Mistral. SDK deadlines never exceed remaining overall time; time already spent cannot be recovered.
- Memory receives at most `MEMORY_TIMEOUT_SECONDS` (default 20) inside the remaining question budget; response cap is 768 tokens. Normal success adds one memory call/exchange, INCLUDING rollover: the sixth brief and paragraph merge share one call. Retries and fallback can add calls within those limits. Gemini Flash-Lite uses minimal thinking, no custom sampling temperature and explicitly disabled automatic function calling. No live calls run in the offline test suite; the separately opt-in live verification script requires `--live`.
- If note generation fails, keep a clearly marked clipped local note and preserve recent full exchanges and any previous paragraph. A safe notice explains the memory limitation in UI and CLI. Do not attempt compression in that exchange.
- If compression fails, keep the old paragraph and six notes, including a clipped local note for the latest exchange. A later exchange retries the combined update using the newest five prior notes and current exchange. During repeated failure, older uncompressed details can be dropped; storage stays bounded. No invented local summary is substituted.
- Provider failures never discard a completed answer, calculation or chart. Memory errors remain notices rather than changing an otherwise successful answer to failure.
- Summaries can omit or misstate details. Important calculations and chart evidence remain separate; resetting clears both the memory and evidence.

## Verification checklist

- [x] Offline six-exchange test produces six notes, then one paragraph and zero notes.
- [x] Twelve-exchange test merges the old paragraph with the next six notes.
- [x] Note/paragraph/context lengths and repeated outage bounds hold.
- [x] Gemini timeout/quota errors use Ministral 14B; configuration errors show safe messages.
- [x] Groq code/narration fallback use working Ministral 14B defaults and respect separate model overrides.
- [x] Primary timeout leaves time for fallback; exhausted global deadline makes no further request.
- [x] Answers/evidence survive memory failures; exchanges are recorded once.
- [x] Reset, dataset replacement and separate sessions isolate/clear summary state.
- [x] UI/CLI show a safe memory notice without raw provider bodies.
- [x] Full offline suite and dependency/whitespace/documentation checks pass.
- [x] Owner-authorized live demo confirms actual keys, account model availability, twelve exchanges, both memory rollovers and early-preference recall. See [LIVE_VERIFICATION.md](LIVE_VERIFICATION.md). Live checks remain separate from the offline test suite.

Completed checks and limitations are recorded in [VALIDATION.md](VALIDATION.md) and [LIVE_VERIFICATION.md](LIVE_VERIFICATION.md).

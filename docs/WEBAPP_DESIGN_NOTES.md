# Working interface design

2026-10-26. The owner authorized a complete React/FastAPI implementation and asked to remove text clutter. This supersedes the mockup's explanatory copy and planning-only status.

## Plan before implementation

Palette: ivory canvas #F7F6F2, stone navigation #ECEBE5, white surface #FFFFFF, charcoal text #252824, teal action #26736B, secondary text #666B63. Dark mode uses the same hierarchy. DM Sans for controls and answers; Newsreader only for the quiet welcome heading and usage count. Local font assets avoid external font requests.

Layout options considered:

```
A. Persistent inspection column     B. Focused chat, on-demand inspection
nav | chat | data + usage            nav | spacious chat
    | input | instructions                | tasks + input
```

Choose B: answers are left aligned; the initial upload action is centered. A narrow sidebar holds the current dataset and links to exchanges in this session. A right-side inspection dialog opens only when needed; it becomes full screen on mobile. The native modal blocks the background and traps focus. It is intentionally not a simultaneously interactive split pane.

## Review against the brief

The accepted cream/serif direction is retained because it was explicitly requested, rather than replaced to satisfy a generic novelty rule. Removed the conversational welcome quote, persistent quota statistics, repeated privacy/infrastructure captions and explanatory cards from the main canvas. The single brand gesture is a lightly tilted chart mark, tying the design to spreadsheet exploration. Task buttons prepare questions without calling a provider. Detailed usage, privacy and calculations are progressively disclosed.

The initial screen says only “Start with your data” and “Upload a spreadsheet, then ask a question.” Dataset state replaces that with “Ask about your data.” No sales copy or decorative quotes.

## Implementation principles

- Native buttons, links, tables and dialogs; explicit focus styles; labels for icon controls.
- Short instructions and errors at the relevant action. No fabricated loading stages.
- Preserve working core analysis, chart evidence, bounded memory, fallbacks and partial results.
- React event handlers own mutations. Poll only active jobs. Load Plotly and its export bundle on demand.
- Session token only in sessionStorage; no conversation or dataset persistence in browser storage.
- Respect reduced motion. Mobile drawers and inspection views must remain keyboard accessible.

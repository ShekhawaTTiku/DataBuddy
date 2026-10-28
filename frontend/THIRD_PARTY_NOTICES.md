# Third-party source adaptations

`src/ChatPrimitives.tsx` adapts the Conversation, ConversationContent,
ConversationScrollButton, Message and MessageActions primitives from
[Vercel AI Elements](https://github.com/vercel/ai-elements/tree/main/packages/elements/src).
Retrieved 2026-10-28. Copyright 2023 Vercel, Inc. Licensed under Apache-2.0;
the license is included in [licenses/Apache-2.0.txt](licenses/Apache-2.0.txt).

Modifications: project CSS and native buttons replace Tailwind/shadcn wrappers;
motion follows the operating system setting, initial scrolling is immediate,
message roles use a local type, and unused export/branching features are omitted.
The upstream `use-stick-to-bottom` package supplies the scrolling implementation.

Other dependencies retain their licenses in the installed npm packages.

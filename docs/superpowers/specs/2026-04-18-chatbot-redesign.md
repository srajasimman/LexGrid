# LexGrid Chatbot UI Redesign — Design Spec

**Date:** 2026-04-18  
**Status:** Approved

---

## Overview

Redesign the LexGrid frontend from a single-query search page into a persistent, ChatGPT-style conversational interface. Conversations are stored in `localStorage` and grouped by date in the sidebar. The visual design follows `DESIGN.md` — warm parchment palette, terracotta accent, near-black dark surfaces.

---

## Layout

Two-panel shell:

| Panel | Width | Background |
|-------|-------|------------|
| Sidebar | 220px fixed | `#141413` (Anthropic Near Black) |
| Main chat | Flex remainder | `#f5f4ed` (Parchment) |

Full viewport height (`100dvh`). No page scroll — each panel scrolls independently.

---

## Sidebar

**Top section (fixed):**
- LexGrid wordmark (`#faf9f5`, Georgia/serif, 15px weight 500) + tagline (`#5e5d59`, 11px sans)
- Border bottom: `1px solid #30302e`
- "New conversation" button: `bg #30302e`, `border #3d3d3a`, `text #b0aea5`, `radius 8px`

**Act filter pills (fixed below new-chat button):**
- Label: `FILTER BY ACT`, uppercase, 10px, `#5e5d59`
- Pills: active = `bg #c96442 text #faf9f5`; inactive = `bg #30302e text #87867f`; `radius 10px`
- Clicking a pill toggles the active filter for new messages. One act active at a time (or none = all acts).
- Selected act is stored in `localStorage` and restored on page load.

**Conversation history (scrollable):**
- Grouped by date: "TODAY", "YESTERDAY", older (date string) — `#5e5d59`, 10px, letter-spacing 0.5px
- Each item: title (first user message, truncated), act badge, message count
- Active conversation: `bg #1e1e1c`, text `#faf9f5`; inactive: text `#87867f`, hover `bg #1e1e1c`
- Clicking loads that conversation into the main panel

---

## Main Chat Panel

**Header (fixed):**
- Background: `#faf9f5`, `border-bottom: 1px solid #e8e6dc`
- Shows active conversation title + act badge + message count
- Empty state: shows "LexGrid" title only

**Message thread (scrollable):**
- Auto-scrolls to bottom on new message
- **User messages**: right-aligned, `bg #141413 text #faf9f5`, `radius 16px 16px 4px 16px`, max-width 70%
- **AI messages**: left-aligned with "L" avatar circle (`bg #141413, text #c96442`), `bg #faf9f5 border #e8e6dc`, `radius 4px 16px 16px 16px`, Georgia serif, `line-height 1.7`
- **Citation badges** below AI message: `bg #faf9f5 border #e8e6dc`, terracotta text, `radius 10px` — each badge links to `/section/[act]/[section]`
- **Performance chip** next to citations: `#87867f`, shows chunk count + latency ms

**Empty state (no conversation selected / new chat):**
- Centered hero: "LexGrid" serif headline, subtitle "Ask anything about Indian Bare Acts", suggestion chips for common queries

**Input bar (fixed bottom):**
- Outer container: `bg #faf9f5 border-top #e8e6dc padding 16px 20px`
- Input pill: `bg #f5f4ed border #e8e6dc radius 16px`, Georgia serif placeholder
- Send button: `bg #c96442 text #faf9f5 radius 10px` — disabled (greyed) when input empty or loading
- Footer text: "Covers BNS, CPC, CrPC, HMA, IDA, IEA, IPC, MVA, NIA" — `#87867f` 10px sans
- Loading state: send button replaced with a pulsing terracotta spinner

---

## Conversation Data Model (localStorage)

```ts
// localStorage key: "lexgrid_conversations"
interface StoredConversation {
  id: string;              // uuid
  title: string;           // first user message (truncated to 60 chars)
  actFilter: string | null;// act code active when conversation started
  createdAt: number;       // unix ms
  messages: StoredMessage[];
}

interface StoredMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];  // from QueryResponse
  latency_ms?: number;
  cache_hit?: boolean;
  timestamp: number;
}

// localStorage key: "lexgrid_active_conversation"
// value: conversation id string

// localStorage key: "lexgrid_act_filter"
// value: act code string or null
```

Conversations are stored as a JSON array. On each new message pair (user + assistant), the conversation is updated in place and written back to `localStorage`. No server-side session state.

---

## Component Structure

```
src/
  app/
    page.tsx              ← Replace with ChatShell (client component)
    globals.css           ← Extend with new color tokens
  components/
    ChatShell.tsx         ← New: two-panel layout wrapper
    Sidebar.tsx           ← New: sidebar with history + filters
    ConversationList.tsx  ← New: scrollable history list
    ChatPanel.tsx         ← New: header + messages + input
    MessageThread.tsx     ← New: renders message list
    MessageBubble.tsx     ← New: single message (user or AI)
    ChatInput.tsx         ← New: input bar with send button
    EmptyState.tsx        ← New: hero shown before first message
    CitationBadge.tsx     ← Existing: keep as-is
```

Existing components (`FilterPanel`, `SearchBar`, `ResultCard`) are replaced by the new components above. `CitationBadge` is reused.

---

## State Management

All state lives in a single `useChatStore` custom hook (no additional libraries):

- `conversations: StoredConversation[]` — loaded from localStorage on mount
- `activeId: string | null` — id of the currently visible conversation
- `actFilter: string | null` — active act filter pill
- Actions: `newConversation()`, `selectConversation(id)`, `sendMessage(query)`, `setActFilter(code)`

`sendMessage` calls `queryLegal()` from the existing `api.ts`, appends user + assistant messages, and persists to localStorage.

---

## Tailwind Extensions

Add to `tailwind.config.ts`:

```ts
colors: {
  parchment: '#f5f4ed',
  ivory: '#faf9f5',
  ink: '#141413',
  'dark-surface': '#30302e',
  terracotta: '#c96442',
  'warm-sand': '#e8e6dc',
  'olive-gray': '#5e5d59',
  'stone-gray': '#87867f',
  'warm-silver': '#b0aea5',
}
```

---

## What Is Not Changing

- `api.ts` — no changes
- `types.ts` — no changes
- `layout.tsx` — font imports and ReactQueryProvider stay
- `CitationBadge.tsx` — reused as-is
- `/section/[act]/[section]` route — unchanged
- Backend — no changes

# Mobile Responsive UI — Design Spec

**Date:** 2026-04-19  
**Status:** Approved  

---

## Problem

The current LexGrid UI uses a fixed 220px sidebar alongside a flex-1 chat panel. On mobile screens, this leaves the chat panel too narrow to be usable. There is no responsive behaviour in any existing component.

## Approach

Responsive design using **Tailwind CSS breakpoints** in the existing components. No user-agent detection, no separate mobile pages. The desktop layout is preserved at `md:` breakpoint and above. Below `md:` (< 768px), a mobile layout takes over.

No new routes, no new pages.

---

## Layout: Desktop vs Mobile

### Desktop (≥ 768px) — unchanged

```
┌──────────────┬────────────────────────────────┐
│  Sidebar     │  ChatPanel                     │
│  220px fixed │  flex-1                        │
└──────────────┴────────────────────────────────┘
```

### Mobile (< 768px)

```
┌──────────────────────────────────────────┐
│  MobileHeader (≡  Title  +)              │
├──────────────────────────────────────────┤
│                                          │
│  ChatPanel (full width)                  │
│                                          │
├──────────────────────────────────────────┤
│  ChatInput                               │
└──────────────────────────────────────────┘
```

When sidebar is open, it overlays from the left:

```
┌────────────────┬─────────────────────────────┐
│  Sidebar       │░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│  ~75% width    │░░ dimmed backdrop ░░░░░░░░░│
│  (slides in)   │░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
└────────────────┴─────────────────────────────┘
```

---

## Components

### `ChatShell` — add mobile sidebar state

Add one boolean: `isSidebarOpen`. Toggle on hamburger click, close on backdrop click or sidebar ✕ button.

```
ChatShell
├── MobileHeader       (new, hidden md:hidden)
├── Sidebar            (existing, adapted)
│   └── close button added for mobile
├── backdrop div       (new, mobile-only overlay)
└── ChatPanel          (existing, unchanged)
```

### `MobileHeader` — new component

Visible only on mobile (`flex md:hidden`). Contains:
- Hamburger button (≡) — left, opens sidebar
- Conversation title — center, truncated
- New conversation (+) button — right, calls `onNewConversation`

Touch targets all ≥ 44px.

### `Sidebar` — minor adaptations

- On desktop: `hidden md:flex` (current `w-[220px] flex flex-col h-full`)  
- On mobile: position `fixed`, full height, `w-[75vw] max-w-[280px]`, slides in via `translate-x-0` / `-translate-x-full`, `z-50`
- Add a ✕ close button inside the sidebar header, visible only on mobile (`md:hidden`)

### `ChatPanel` header

On desktop: shows title and message count as today.  
On mobile: the `ChatPanel` header row is hidden (`hidden md:flex`) since `MobileHeader` covers that role.

---

## State

Single addition to `ChatShell`:

```ts
const [isSidebarOpen, setIsSidebarOpen] = useState(false);
```

- `hamburgerClick` → `setIsSidebarOpen(true)`
- `backdropClick` → `setIsSidebarOpen(false)`
- `closeButtonClick` → `setIsSidebarOpen(false)`
- Route change / new conversation → `setIsSidebarOpen(false)`

---

## Animations

Sidebar slide: `transition-transform duration-200 ease-in-out`  
Backdrop fade: `transition-opacity duration-200`

Both are CSS-only via Tailwind classes toggled by `isSidebarOpen`.

---

## Files Changed

| File | Change |
|---|---|
| `ui/src/components/ChatShell.tsx` | Add `isSidebarOpen` state, render `MobileHeader` + backdrop, pass open/close handlers |
| `ui/src/components/Sidebar.tsx` | Add mobile positioning classes, ✕ close button, accept `onClose` prop |
| `ui/src/components/ChatPanel.tsx` | Hide existing header on mobile (`hidden md:flex`) |
| `ui/src/components/MobileHeader.tsx` | New component |

No changes to `chatStore`, `api`, routing, or backend.

---

## Out of Scope

- No changes to desktop layout
- No changes to `SectionViewer` or `/section/[act]/[section]` route (not commonly accessed on mobile in this phase)
- No PWA / install prompt

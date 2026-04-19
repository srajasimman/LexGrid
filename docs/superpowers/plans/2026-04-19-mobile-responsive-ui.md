# Mobile Responsive UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the LexGrid chat UI usable on mobile by adding a hamburger header and slide-in sidebar overlay for screens narrower than 768px (Tailwind `md:` breakpoint).

**Architecture:** `ChatShell` gains one `isSidebarOpen` boolean state and renders a new `MobileHeader` component and a backdrop div on mobile. `Sidebar` gains mobile-specific positioning classes and a close button. `ChatPanel`'s header row is hidden on mobile since `MobileHeader` covers that role. Desktop layout is completely unchanged.

**Tech Stack:** Next.js 14 (App Router), React, Tailwind CSS, TypeScript, Lucide React icons.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `ui/src/components/MobileHeader.tsx` | **Create** | Hamburger + title + new-chat button, mobile-only |
| `ui/src/components/ChatShell.tsx` | **Modify** | Add `isSidebarOpen` state, backdrop, wire `MobileHeader` |
| `ui/src/components/Sidebar.tsx` | **Modify** | Mobile slide-in positioning, `onClose` prop, ✕ button |
| `ui/src/components/ChatPanel.tsx` | **Modify** | Hide existing header on mobile |

No changes to: `chatStore`, `api`, routing, backend, `globals.css`.

---

### Task 1: Create `MobileHeader` component

**Files:**
- Create: `ui/src/components/MobileHeader.tsx`

- [ ] **Step 1: Create the file**

```tsx
'use client';

import { Menu, Plus } from 'lucide-react';

interface Props {
  title: string;
  onOpenSidebar: () => void;
  onNewConversation: () => void;
}

export default function MobileHeader({ title, onOpenSidebar, onNewConversation }: Props) {
  return (
    <div className="flex md:hidden items-center justify-between px-3 py-2.5 bg-ivory border-b border-warm-sand flex-shrink-0">
      <button
        onClick={onOpenSidebar}
        className="w-11 h-11 flex items-center justify-center rounded-lg text-ink hover:bg-warm-sand transition-colors"
        aria-label="Open menu"
      >
        <Menu className="w-5 h-5" />
      </button>
      <span className="font-sans font-medium text-sm text-ink truncate px-2 flex-1 text-center">
        {title || 'LexGrid'}
      </span>
      <button
        onClick={onNewConversation}
        className="w-11 h-11 flex items-center justify-center rounded-lg bg-terracotta text-ivory hover:bg-terracotta/90 transition-colors"
        aria-label="New conversation"
      >
        <Plus className="w-5 h-5" />
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Verify the file was created at the right path**

```bash
ls ui/src/components/MobileHeader.tsx
```

Expected: file listed without error.

- [ ] **Step 3: Commit**

```bash
git add ui/src/components/MobileHeader.tsx
git commit -m "feat: add MobileHeader component for mobile nav"
```

---

### Task 2: Add mobile slide-in behaviour to `Sidebar`

**Files:**
- Modify: `ui/src/components/Sidebar.tsx`

- [ ] **Step 1: Read current file to confirm starting state**

The outer `<div>` currently has: `className="w-[220px] flex-shrink-0 bg-ink flex flex-col h-full"`

- [ ] **Step 2: Replace the outer div and add close button**

Replace the entire `Sidebar` function body with:

```tsx
'use client';

import { Plus, X } from 'lucide-react';
import ConversationList from '@/components/ConversationList';
import type { StoredConversation } from '@/lib/chatStore';

const ACT_CODES = ['BNS', 'CPC', 'CrPC', 'HMA', 'IDA', 'IEA', 'IPC', 'MVA', 'NIA'];

interface Props {
  conversations: StoredConversation[];
  activeId: string | null;
  actFilter: string | null;
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
  onSetActFilter: (code: string | null) => void;
  onPinConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onClose?: () => void;
}

export default function Sidebar({
  conversations,
  activeId,
  actFilter,
  onNewConversation,
  onSelectConversation,
  onSetActFilter,
  onPinConversation,
  onDeleteConversation,
  onClose,
}: Props) {
  function toggleAct(code: string) {
    onSetActFilter(actFilter === code ? null : code);
  }

  return (
    <div className="w-[220px] flex-shrink-0 bg-ink flex flex-col h-full">
      {/* Logo + close button (close only shown on mobile) */}
      <div className="px-4 py-4 border-b border-dark-surface flex-shrink-0 flex items-start justify-between">
        <div>
          <p className="font-serif text-[15px] font-medium text-ivory">LexGrid</p>
          <p className="font-sans text-[11px] text-olive-gray mt-0.5">Indian Legal Research</p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="md:hidden w-8 h-8 flex items-center justify-center text-olive-gray hover:text-warm-silver transition-colors"
            aria-label="Close menu"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* New conversation */}
      <div className="px-3 pt-3 flex-shrink-0">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center gap-2 bg-dark-surface border border-dark-border rounded-lg px-3 py-2 text-warm-silver text-xs font-sans hover:bg-dark-elevated transition-colors"
        >
          <Plus className="w-4 h-4" />
          New conversation
        </button>
      </div>

      {/* Act filter pills */}
      <div className="px-3 pt-3 pb-2 flex-shrink-0">
        <p className="text-olive-gray text-[10px] font-sans tracking-[0.5px] mb-2">FILTER BY ACT</p>
        <div className="flex flex-wrap gap-1.5">
          {ACT_CODES.map((code) => (
            <button
              key={code}
              onClick={() => toggleAct(code)}
              className={`px-2.5 py-0.5 rounded-xl text-[10px] font-sans transition-colors ${
                actFilter === code
                  ? 'bg-terracotta text-ivory'
                  : 'bg-dark-surface text-stone-gray hover:text-warm-silver'
              }`}
            >
              {code}
            </button>
          ))}
        </div>
      </div>

      {/* Scrollable conversation list */}
      <div className="flex-1 overflow-y-auto px-1 pb-4">
        <ConversationList
          conversations={conversations}
          activeId={activeId}
          onSelect={onSelectConversation}
          onPin={onPinConversation}
          onDelete={onDeleteConversation}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add ui/src/components/Sidebar.tsx
git commit -m "feat: add onClose prop and mobile close button to Sidebar"
```

---

### Task 3: Update `ChatShell` — add mobile state, backdrop, and layout

**Files:**
- Modify: `ui/src/components/ChatShell.tsx`

- [ ] **Step 1: Replace the full file**

```tsx
'use client';

import { useState } from 'react';
import Sidebar from '@/components/Sidebar';
import ChatPanel from '@/components/ChatPanel';
import MobileHeader from '@/components/MobileHeader';
import { useChatStore } from '@/lib/chatStore';

export default function ChatShell() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const {
    conversations,
    activeId,
    actFilter,
    isLoading,
    activeConversation,
    newConversation,
    selectConversation,
    setActFilter,
    sendMessage,
    pinConversation,
    deleteConversation,
  } = useChatStore();

  function handleSelectConversation(id: string) {
    selectConversation(id);
    setIsSidebarOpen(false);
  }

  function handleNewConversation() {
    newConversation();
    setIsSidebarOpen(false);
  }

  return (
    <div className="flex h-full">
      {/* Mobile backdrop */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar — desktop: static; mobile: fixed slide-in overlay */}
      <div
        className={`
          fixed inset-y-0 left-0 z-50 transition-transform duration-200 ease-in-out
          md:static md:translate-x-0 md:z-auto md:transition-none
          ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <Sidebar
          conversations={conversations}
          activeId={activeId}
          actFilter={actFilter}
          onNewConversation={handleNewConversation}
          onSelectConversation={handleSelectConversation}
          onSetActFilter={setActFilter}
          onPinConversation={pinConversation}
          onDeleteConversation={deleteConversation}
          onClose={() => setIsSidebarOpen(false)}
        />
      </div>

      {/* Main area */}
      <div className="flex-1 min-w-0 flex flex-col">
        <MobileHeader
          title={activeConversation?.title ?? ''}
          onOpenSidebar={() => setIsSidebarOpen(true)}
          onNewConversation={handleNewConversation}
        />
        <ChatPanel
          conversation={activeConversation}
          isLoading={isLoading}
          onSend={sendMessage}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add ui/src/components/ChatShell.tsx
git commit -m "feat: add mobile sidebar overlay and MobileHeader to ChatShell"
```

---

### Task 4: Hide `ChatPanel` header on mobile

**Files:**
- Modify: `ui/src/components/ChatPanel.tsx`

- [ ] **Step 1: Add `hidden md:flex` to the header div**

Find the header div (currently line 21):
```tsx
<div className="flex items-center justify-between px-5 py-3.5 bg-ivory border-b border-warm-sand flex-shrink-0">
```

Replace with:
```tsx
<div className="hidden md:flex items-center justify-between px-5 py-3.5 bg-ivory border-b border-warm-sand flex-shrink-0">
```

- [ ] **Step 2: Commit**

```bash
git add ui/src/components/ChatPanel.tsx
git commit -m "feat: hide ChatPanel header on mobile (MobileHeader takes over)"
```

---

### Task 5: Smoke-test on mobile viewport

- [ ] **Step 1: Start the UI dev server**

```bash
cd ui && npm run dev
```

Open `http://localhost:3000` in Chrome DevTools with a mobile viewport (e.g. iPhone 12 — 390×844).

- [ ] **Step 2: Verify mobile layout**

Checklist:
- [ ] Sidebar is NOT visible on load
- [ ] `MobileHeader` shows: hamburger left, title center, + right
- [ ] Tapping hamburger opens sidebar from left with animation
- [ ] Backdrop (dimmed area) is visible to the right of sidebar
- [ ] Tapping backdrop closes sidebar
- [ ] Tapping ✕ in sidebar header closes sidebar
- [ ] Selecting a conversation closes sidebar and loads it
- [ ] Tapping + in `MobileHeader` starts a new conversation and closes sidebar
- [ ] Act filter pills work inside the open sidebar
- [ ] Chat input is usable (full width, keyboard doesn't obscure it)

- [ ] **Step 3: Verify desktop layout unchanged**

Switch DevTools to desktop viewport (≥ 768px):
- [ ] Sidebar renders as static 220px column on the left (no hamburger)
- [ ] `MobileHeader` is not visible
- [ ] `ChatPanel` header (title + message count) is visible
- [ ] Everything else works exactly as before

- [ ] **Step 4: Commit if any minor fixups were needed**

```bash
git add -p
git commit -m "fix: mobile responsive tweaks from smoke test"
```

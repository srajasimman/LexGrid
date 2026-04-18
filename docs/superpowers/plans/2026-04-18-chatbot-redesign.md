# Chatbot UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-query search page with a persistent ChatGPT-style conversational interface backed by localStorage, using the DESIGN.md warm parchment palette.

**Architecture:** A two-panel shell (220px dark sidebar + flex parchment chat area) rendered from `page.tsx`. All conversation state lives in a `useChatStore` hook that reads/writes three `localStorage` keys. The existing `api.ts` and `types.ts` are untouched; `CitationBadge` is reused as-is.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript, Tailwind CSS 3, `@tanstack/react-query` (already installed), `lucide-react` (already installed), no new dependencies.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `ui/tailwind.config.ts` | Add DESIGN.md colour tokens |
| Modify | `ui/src/app/globals.css` | Remove stale CSS vars, add `html,body { height:100% }` |
| Modify | `ui/src/app/layout.tsx` | Add `h-full` to `<html>` and `<body>` |
| Create | `ui/src/lib/chatStore.ts` | `useChatStore` hook + localStorage persistence |
| Modify | `ui/src/app/page.tsx` | Replace search page with `<ChatShell />` |
| Create | `ui/src/components/ChatShell.tsx` | Two-panel layout wrapper |
| Create | `ui/src/components/Sidebar.tsx` | Logo, new-chat button, act pills, conversation list |
| Create | `ui/src/components/ConversationList.tsx` | Date-grouped scrollable history |
| Create | `ui/src/components/EmptyState.tsx` | Hero shown before first message |
| Create | `ui/src/components/ChatPanel.tsx` | Header + MessageThread + ChatInput |
| Create | `ui/src/components/MessageThread.tsx` | Scrollable message list, auto-scroll |
| Create | `ui/src/components/MessageBubble.tsx` | Single user or AI message bubble |
| Create | `ui/src/components/ChatInput.tsx` | Textarea + send button + footer text |

---

## Task 1: Extend Tailwind colour tokens

**Files:**
- Modify: `ui/tailwind.config.ts`

- [ ] **Step 1: Replace the colours block in tailwind.config.ts**

Open `ui/tailwind.config.ts` and replace the existing `colors` block inside `theme.extend` with:

```ts
colors: {
  parchment: '#f5f4ed',
  ivory: '#faf9f5',
  ink: '#141413',
  'dark-surface': '#30302e',
  'dark-elevated': '#1e1e1c',
  'dark-border': '#3d3d3a',
  terracotta: '#c96442',
  'warm-sand': '#e8e6dc',
  'olive-gray': '#5e5d59',
  'stone-gray': '#87867f',
  'warm-silver': '#b0aea5',
},
```

The full file becomes:

```ts
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        serif: ['var(--font-crimson)', 'Georgia', 'Cambria', 'serif'],
      },
      colors: {
        parchment: '#f5f4ed',
        ivory: '#faf9f5',
        ink: '#141413',
        'dark-surface': '#30302e',
        'dark-elevated': '#1e1e1c',
        'dark-border': '#3d3d3a',
        terracotta: '#c96442',
        'warm-sand': '#e8e6dc',
        'olive-gray': '#5e5d59',
        'stone-gray': '#87867f',
        'warm-silver': '#b0aea5',
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 2: Commit**

```bash
cd ui && git add tailwind.config.ts && git commit -m "style: add DESIGN.md colour tokens to Tailwind"
```

---

## Task 2: Fix global CSS and layout for full-height shell

**Files:**
- Modify: `ui/src/app/globals.css`
- Modify: `ui/src/app/layout.tsx`

- [ ] **Step 1: Replace globals.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --legal-serif: 'Crimson Text', Georgia, Cambria, serif;
}

html,
body {
  height: 100%;
}
```

- [ ] **Step 2: Update layout.tsx to propagate full height**

Replace the `<body>` className from `"font-sans antialiased bg-parchment text-ink min-h-screen"` to `"font-sans antialiased bg-parchment text-ink h-full"`, and add `className="h-full"` to `<html>`:

```tsx
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${crimsonText.variable} h-full`}>
      <body className="font-sans antialiased bg-parchment text-ink h-full">
        <ReactQueryProvider>{children}</ReactQueryProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add src/app/globals.css src/app/layout.tsx && git commit -m "style: full-height root for chat shell"
```

---

## Task 3: Build the useChatStore hook

**Files:**
- Create: `ui/src/lib/chatStore.ts`

This hook is the single source of truth. It owns all localStorage reads/writes and exposes actions to the components.

- [ ] **Step 1: Create ui/src/lib/chatStore.ts**

```ts
'use client';

import { useState, useEffect, useCallback } from 'react';
import { queryLegal } from '@/lib/api';
import type { Citation } from '@/lib/types';

// ─── Data model ───────────────────────────────────────────────────────────────

export interface StoredMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  latency_ms?: number;
  cache_hit?: boolean;
  chunks_retrieved?: number;
  timestamp: number;
}

export interface StoredConversation {
  id: string;
  title: string;
  actFilter: string | null;
  createdAt: number;
  messages: StoredMessage[];
}

// ─── localStorage keys ────────────────────────────────────────────────────────

const LS_CONVERSATIONS = 'lexgrid_conversations';
const LS_ACTIVE = 'lexgrid_active_conversation';
const LS_ACT_FILTER = 'lexgrid_act_filter';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function loadConversations(): StoredConversation[] {
  try {
    const raw = localStorage.getItem(LS_CONVERSATIONS);
    return raw ? (JSON.parse(raw) as StoredConversation[]) : [];
  } catch {
    return [];
  }
}

function saveConversations(conversations: StoredConversation[]): void {
  localStorage.setItem(LS_CONVERSATIONS, JSON.stringify(conversations));
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export interface ChatStore {
  conversations: StoredConversation[];
  activeId: string | null;
  actFilter: string | null;
  isLoading: boolean;
  activeConversation: StoredConversation | null;
  newConversation: () => void;
  selectConversation: (id: string) => void;
  setActFilter: (code: string | null) => void;
  sendMessage: (query: string) => Promise<void>;
}

export function useChatStore(): ChatStore {
  const [conversations, setConversations] = useState<StoredConversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [actFilter, setActFilterState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Load from localStorage on mount (client-only)
  useEffect(() => {
    setConversations(loadConversations());
    setActiveId(localStorage.getItem(LS_ACTIVE));
    setActFilterState(localStorage.getItem(LS_ACT_FILTER));
  }, []);

  const activeConversation = conversations.find((c) => c.id === activeId) ?? null;

  const newConversation = useCallback(() => {
    setActiveId(null);
    localStorage.removeItem(LS_ACTIVE);
  }, []);

  const selectConversation = useCallback((id: string) => {
    setActiveId(id);
    localStorage.setItem(LS_ACTIVE, id);
  }, []);

  const setActFilter = useCallback((code: string | null) => {
    setActFilterState(code);
    if (code) {
      localStorage.setItem(LS_ACT_FILTER, code);
    } else {
      localStorage.removeItem(LS_ACT_FILTER);
    }
  }, []);

  const sendMessage = useCallback(
    async (query: string) => {
      setIsLoading(true);

      // Build or retrieve the active conversation
      let convId = activeId;
      let updatedConversations = [...conversations];

      if (!convId) {
        const newConv: StoredConversation = {
          id: generateId(),
          title: query.slice(0, 60),
          actFilter,
          createdAt: Date.now(),
          messages: [],
        };
        updatedConversations = [newConv, ...updatedConversations];
        convId = newConv.id;
        setActiveId(convId);
        localStorage.setItem(LS_ACTIVE, convId);
      }

      // Append user message
      const userMsg: StoredMessage = {
        role: 'user',
        content: query,
        timestamp: Date.now(),
      };

      updatedConversations = updatedConversations.map((c) =>
        c.id === convId ? { ...c, messages: [...c.messages, userMsg] } : c,
      );
      setConversations(updatedConversations);
      saveConversations(updatedConversations);

      try {
        const response = await queryLegal({
          query,
          act_filter: actFilter ?? undefined,
          top_k: 5,
          use_cache: true,
        });

        const assistantMsg: StoredMessage = {
          role: 'assistant',
          content: response.answer,
          citations: response.citations,
          latency_ms: response.total_ms ?? response.latency_ms,
          cache_hit: response.cache_hit,
          chunks_retrieved: response.chunks_retrieved ?? response.retrieved_chunks.length,
          timestamp: Date.now(),
        };

        updatedConversations = updatedConversations.map((c) =>
          c.id === convId ? { ...c, messages: [...c.messages, assistantMsg] } : c,
        );
      } catch (err) {
        const errorMsg: StoredMessage = {
          role: 'assistant',
          content: `Sorry, something went wrong. ${err instanceof Error ? err.message : 'Please try again.'}`,
          timestamp: Date.now(),
        };
        updatedConversations = updatedConversations.map((c) =>
          c.id === convId ? { ...c, messages: [...c.messages, errorMsg] } : c,
        );
      } finally {
        setConversations(updatedConversations);
        saveConversations(updatedConversations);
        setIsLoading(false);
      }
    },
    [activeId, actFilter, conversations],
  );

  return {
    conversations,
    activeId,
    actFilter,
    isLoading,
    activeConversation,
    newConversation,
    selectConversation,
    setActFilter,
    sendMessage,
  };
}
```

- [ ] **Step 2: Verify TypeScript compiles (from ui/)**

```bash
npx tsc --noEmit
```

Expected: no errors related to `chatStore.ts`.

- [ ] **Step 3: Commit**

```bash
git add src/lib/chatStore.ts && git commit -m "feat: useChatStore hook with localStorage persistence"
```

---

## Task 4: EmptyState component

**Files:**
- Create: `ui/src/components/EmptyState.tsx`

- [ ] **Step 1: Create ui/src/components/EmptyState.tsx**

```tsx
'use client';

interface Props {
  onSuggestion: (query: string) => void;
}

const SUGGESTIONS = [
  'What is Section 302 IPC?',
  'Bail conditions under CrPC Section 437',
  'Grounds for divorce under HMA',
  'What is culpable homicide under BNS?',
];

export default function EmptyState({ onSuggestion }: Props) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 text-center gap-8">
      <div>
        <h1 className="font-serif text-4xl font-medium text-ink leading-tight">LexGrid</h1>
        <p className="mt-2 text-olive-gray font-sans text-base">
          Ask anything about Indian Bare Acts
        </p>
      </div>

      <div className="flex flex-wrap justify-center gap-3 max-w-lg">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSuggestion(s)}
            className="px-4 py-2 bg-ivory border border-warm-sand rounded-2xl text-sm font-sans text-olive-gray hover:bg-warm-sand hover:text-ink transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/EmptyState.tsx && git commit -m "feat: EmptyState hero with suggestion chips"
```

---

## Task 5: MessageBubble component

**Files:**
- Create: `ui/src/components/MessageBubble.tsx`

- [ ] **Step 1: Create ui/src/components/MessageBubble.tsx**

```tsx
'use client';

import CitationBadge from '@/components/CitationBadge';
import type { StoredMessage } from '@/lib/chatStore';

interface Props {
  message: StoredMessage;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="bg-ink text-ivory rounded-[16px_16px_4px_16px] px-4 py-2.5 max-w-[70%] text-sm font-sans leading-relaxed">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 items-start">
      {/* Avatar */}
      <div className="w-7 h-7 rounded-full bg-ink flex items-center justify-center flex-shrink-0 mt-0.5">
        <span className="text-terracotta text-xs font-semibold font-sans">L</span>
      </div>

      <div className="flex-1 min-w-0">
        {/* Answer */}
        <div className="bg-ivory border border-warm-sand rounded-[4px_16px_16px_16px] px-4 py-3 text-sm font-serif leading-[1.7] text-ink whitespace-pre-wrap">
          {message.content}
        </div>

        {/* Citations + perf chip */}
        {(message.citations && message.citations.length > 0) || message.latency_ms ? (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {message.citations?.map((c, i) => (
              <CitationBadge key={`${c.act_code}-${c.section_number}-${i}`} citation={c} />
            ))}
            {message.latency_ms != null && (
              <span className="text-stone-gray font-sans text-xs">
                {message.chunks_retrieved} sections
                {message.latency_ms > 0 && ` · ${message.latency_ms.toFixed(0)}ms`}
                {message.cache_hit && ' · ⚡ cached'}
              </span>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/MessageBubble.tsx && git commit -m "feat: MessageBubble for user and AI messages"
```

---

## Task 6: MessageThread component

**Files:**
- Create: `ui/src/components/MessageThread.tsx`

- [ ] **Step 1: Create ui/src/components/MessageThread.tsx**

```tsx
'use client';

import { useEffect, useRef } from 'react';
import MessageBubble from '@/components/MessageBubble';
import type { StoredMessage } from '@/lib/chatStore';

interface Props {
  messages: StoredMessage[];
  isLoading: boolean;
}

export default function MessageThread({ messages, isLoading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-5">
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}

      {isLoading && (
        <div className="flex gap-3 items-start">
          <div className="w-7 h-7 rounded-full bg-ink flex items-center justify-center flex-shrink-0 mt-0.5">
            <span className="text-terracotta text-xs font-semibold font-sans">L</span>
          </div>
          <div className="bg-ivory border border-warm-sand rounded-[4px_16px_16px_16px] px-4 py-3">
            <div className="flex gap-1 items-center">
              <span className="w-1.5 h-1.5 rounded-full bg-terracotta animate-bounce [animation-delay:0ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-terracotta animate-bounce [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-terracotta animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/MessageThread.tsx && git commit -m "feat: MessageThread with auto-scroll and loading indicator"
```

---

## Task 7: ChatInput component

**Files:**
- Create: `ui/src/components/ChatInput.tsx`

- [ ] **Step 1: Create ui/src/components/ChatInput.tsx**

```tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

interface Props {
  onSubmit: (query: string) => void;
  isLoading: boolean;
}

export default function ChatInput({ onSubmit, isLoading }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    onSubmit(trimmed);
    setValue('');
  }

  const disabled = !value.trim() || isLoading;

  return (
    <div className="px-5 py-4 border-t border-warm-sand bg-ivory">
      <div className="flex items-end gap-3 bg-parchment border border-warm-sand rounded-2xl px-4 py-2.5">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a legal question…"
          rows={1}
          className="flex-1 bg-transparent border-none outline-none resize-none font-serif text-sm text-ink placeholder:text-stone-gray leading-relaxed max-h-40"
        />
        <button
          onClick={submit}
          disabled={disabled}
          className="flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-colors
            bg-terracotta text-ivory
            disabled:bg-warm-sand disabled:text-stone-gray disabled:cursor-not-allowed"
          aria-label="Send"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      <p className="text-center mt-2 text-xs font-sans text-stone-gray">
        Covers BNS, CPC, CrPC, HMA, IDA, IEA, IPC, MVA, NIA
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/ChatInput.tsx && git commit -m "feat: ChatInput with auto-resize textarea and send button"
```

---

## Task 8: ChatPanel component

**Files:**
- Create: `ui/src/components/ChatPanel.tsx`

- [ ] **Step 1: Create ui/src/components/ChatPanel.tsx**

```tsx
'use client';

import EmptyState from '@/components/EmptyState';
import MessageThread from '@/components/MessageThread';
import ChatInput from '@/components/ChatInput';
import type { StoredConversation } from '@/lib/chatStore';

interface Props {
  conversation: StoredConversation | null;
  isLoading: boolean;
  onSend: (query: string) => void;
}

export default function ChatPanel({ conversation, isLoading, onSend }: Props) {
  const messages = conversation?.messages ?? [];
  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-col h-full bg-parchment">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 bg-ivory border-b border-warm-sand flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-sans font-medium text-sm text-ink truncate">
            {conversation?.title ?? 'LexGrid'}
          </span>
          {conversation?.actFilter && (
            <span className="px-2 py-0.5 bg-warm-sand text-olive-gray rounded-lg text-xs font-sans flex-shrink-0">
              {conversation.actFilter}
            </span>
          )}
        </div>
        {hasMessages && (
          <span className="text-stone-gray text-xs font-sans flex-shrink-0">
            {messages.length} message{messages.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Body */}
      {hasMessages || isLoading ? (
        <MessageThread messages={messages} isLoading={isLoading} />
      ) : (
        <EmptyState onSuggestion={onSend} />
      )}

      {/* Input */}
      <ChatInput onSubmit={onSend} isLoading={isLoading} />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/ChatPanel.tsx && git commit -m "feat: ChatPanel assembles header, thread, and input"
```

---

## Task 9: ConversationList component

**Files:**
- Create: `ui/src/components/ConversationList.tsx`

- [ ] **Step 1: Create ui/src/components/ConversationList.tsx**

```tsx
'use client';

import type { StoredConversation } from '@/lib/chatStore';

interface Props {
  conversations: StoredConversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
}

function dateLabel(ts: number): string {
  const d = new Date(ts);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - d.getTime()) / 86_400_000);
  if (diffDays === 0) return 'TODAY';
  if (diffDays === 1) return 'YESTERDAY';
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase();
}

export default function ConversationList({ conversations, activeId, onSelect }: Props) {
  if (conversations.length === 0) {
    return (
      <p className="text-stone-gray text-xs font-sans px-3 py-4">No conversations yet.</p>
    );
  }

  // Group by date label
  const groups: { label: string; items: StoredConversation[] }[] = [];
  for (const conv of conversations) {
    const label = dateLabel(conv.createdAt);
    const existing = groups.find((g) => g.label === label);
    if (existing) {
      existing.items.push(conv);
    } else {
      groups.push({ label, items: [conv] });
    }
  }

  return (
    <div className="flex flex-col gap-1">
      {groups.map((group) => (
        <div key={group.label}>
          <p className="text-olive-gray text-[10px] font-sans tracking-[0.5px] px-3 py-1.5 mt-2">
            {group.label}
          </p>
          {group.items.map((conv) => {
            const isActive = conv.id === activeId;
            return (
              <button
                key={conv.id}
                onClick={() => onSelect(conv.id)}
                className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
                  isActive
                    ? 'bg-dark-elevated text-ivory'
                    : 'text-stone-gray hover:bg-dark-elevated hover:text-ivory'
                }`}
              >
                <p className="text-xs font-sans truncate">{conv.title}</p>
                <p className="text-[10px] font-sans text-olive-gray mt-0.5">
                  {conv.actFilter ?? 'All acts'} · {conv.messages.length} msg
                </p>
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/ConversationList.tsx && git commit -m "feat: ConversationList with date grouping"
```

---

## Task 10: Sidebar component

**Files:**
- Create: `ui/src/components/Sidebar.tsx`

- [ ] **Step 1: Create ui/src/components/Sidebar.tsx**

```tsx
'use client';

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
}

export default function Sidebar({
  conversations,
  activeId,
  actFilter,
  onNewConversation,
  onSelectConversation,
  onSetActFilter,
}: Props) {
  function toggleAct(code: string) {
    onSetActFilter(actFilter === code ? null : code);
  }

  return (
    <div className="w-[220px] flex-shrink-0 bg-ink flex flex-col h-full">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-dark-surface flex-shrink-0">
        <p className="font-serif text-[15px] font-medium text-ivory">LexGrid</p>
        <p className="font-sans text-[11px] text-olive-gray mt-0.5">Indian Legal Research</p>
      </div>

      {/* New conversation */}
      <div className="px-3 pt-3 flex-shrink-0">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center gap-2 bg-dark-surface border border-dark-border rounded-lg px-3 py-2 text-warm-silver text-xs font-sans hover:bg-dark-elevated transition-colors"
        >
          <span className="text-base leading-none">＋</span>
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
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/Sidebar.tsx && git commit -m "feat: Sidebar with logo, new-chat button, act filters, history"
```

---

## Task 11: ChatShell wrapper

**Files:**
- Create: `ui/src/components/ChatShell.tsx`

- [ ] **Step 1: Create ui/src/components/ChatShell.tsx**

```tsx
'use client';

import Sidebar from '@/components/Sidebar';
import ChatPanel from '@/components/ChatPanel';
import { useChatStore } from '@/lib/chatStore';

export default function ChatShell() {
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
  } = useChatStore();

  return (
    <div className="flex h-full">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        actFilter={actFilter}
        onNewConversation={newConversation}
        onSelectConversation={selectConversation}
        onSetActFilter={setActFilter}
      />
      <div className="flex-1 min-w-0">
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
git add src/components/ChatShell.tsx && git commit -m "feat: ChatShell two-panel layout"
```

---

## Task 12: Wire up page.tsx

**Files:**
- Modify: `ui/src/app/page.tsx`

- [ ] **Step 1: Replace page.tsx**

```tsx
import ChatShell from '@/components/ChatShell';

export default function HomePage() {
  return <ChatShell />;
}
```

- [ ] **Step 2: Run the dev server and verify**

```bash
cd ui && npm run dev
```

Open http://localhost:3000. Verify:
- Two-panel layout renders (dark sidebar left, parchment chat right)
- "New conversation" button is visible
- All 9 act filter pills are present
- Empty state hero appears in chat panel with suggestion chips
- Clicking a suggestion chip populates the input and sends a query
- AI response renders with citation badges
- Conversation appears in sidebar history
- Refreshing the page restores the conversation from localStorage

- [ ] **Step 3: Verify TypeScript**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add src/app/page.tsx && git commit -m "feat: replace search page with ChatShell"
```

---

## Task 13: Cleanup — remove replaced components

**Files:**
- Delete: `ui/src/components/SearchBar.tsx`
- Delete: `ui/src/components/FilterPanel.tsx`
- Delete: `ui/src/components/ResultCard.tsx`

- [ ] **Step 1: Delete the old components**

```bash
rm ui/src/components/SearchBar.tsx ui/src/components/FilterPanel.tsx ui/src/components/ResultCard.tsx
```

- [ ] **Step 2: Verify build still passes**

```bash
cd ui && npm run build
```

Expected: no errors. If any import of the deleted files remains, remove it.

- [ ] **Step 3: Commit**

```bash
git add -u && git commit -m "chore: remove old SearchBar, FilterPanel, ResultCard components"
```

---

## Self-Review

**Spec coverage:**
- ✅ Two-panel layout (220px dark sidebar + parchment chat) — Task 11
- ✅ Full viewport height, independent panel scroll — Tasks 2, 11
- ✅ Logo, new-chat button, act filter pills — Task 10
- ✅ Act filter stored in localStorage, restored on load — Task 3
- ✅ Conversation history grouped by date — Task 9
- ✅ Active/inactive conversation styling — Task 9
- ✅ Chat header with title + act badge + message count — Task 8
- ✅ Empty state hero with suggestion chips — Task 4
- ✅ User bubbles (right-aligned, ink bg) — Task 5
- ✅ AI bubbles (left-aligned, avatar, serif, warm border) — Task 5
- ✅ Citation badges reusing CitationBadge — Task 5
- ✅ Performance chip (chunks + latency + cache) — Task 5
- ✅ Auto-scroll to bottom — Task 6
- ✅ Loading indicator (bouncing dots) — Task 6
- ✅ Textarea input with send button, disabled state — Task 7
- ✅ Footer text listing all 9 acts — Task 7
- ✅ Tailwind colour tokens from DESIGN.md — Task 1
- ✅ localStorage data model (StoredConversation, StoredMessage) — Task 3
- ✅ sendMessage calls existing queryLegal() — Task 3
- ✅ Deleted old components — Task 13

**Placeholder scan:** None found.

**Type consistency:** `StoredConversation` and `StoredMessage` are defined once in `chatStore.ts` and imported by all components. `Citation` is imported from existing `types.ts`. `useChatStore` return type is explicit and matches all call sites.

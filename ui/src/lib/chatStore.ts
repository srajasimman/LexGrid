'use client';

import { useState, useEffect, useCallback } from 'react';
import { streamQuery } from '@/lib/api';
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
  pinned?: boolean;
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
  try {
    localStorage.setItem(LS_CONVERSATIONS, JSON.stringify(conversations));
  } catch {
    // QuotaExceededError — silently tolerate; in-memory state is still correct
  }
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
  pinConversation: (id: string) => void;
  deleteConversation: (id: string) => void;
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

  // NOTE: sendMessage captures the `conversations` snapshot at call time.
  // The isLoading guard prevents re-entry from the UI, but programmatic
  // rapid-fire calls could corrupt state. Full fix requires functional
  // updater form in setConversations — tracked as a follow-up.
  const sendMessage = useCallback(
    async (query: string) => {
      if (isLoading) return;
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

      // Insert an empty assistant message placeholder to stream into
      const assistantMsg: StoredMessage = {
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
      };
      updatedConversations = updatedConversations.map((c) =>
        c.id === convId ? { ...c, messages: [...c.messages, assistantMsg] } : c,
      );
      setConversations(updatedConversations);

      try {
        await streamQuery(
          { query, act_filter: actFilter ?? undefined, top_k: 5, use_cache: true },
          (event) => {
            if (event.type === 'token') {
              // Append token to the last message in the active conversation
              setConversations((prev) => {
                const updated = prev.map((c) => {
                  if (c.id !== convId) return c;
                  const msgs = [...c.messages];
                  const last = msgs[msgs.length - 1];
                  msgs[msgs.length - 1] = { ...last, content: last.content + event.content };
                  return { ...c, messages: msgs };
                });
                return updated;
              });
            } else if (event.type === 'citations') {
              setConversations((prev) => {
                const updated = prev.map((c) => {
                  if (c.id !== convId) return c;
                  const msgs = [...c.messages];
                  const last = msgs[msgs.length - 1];
                  msgs[msgs.length - 1] = {
                    ...last,
                    citations: event.citations as Citation[],
                    latency_ms: Date.now() - assistantMsg.timestamp,
                  };
                  return { ...c, messages: msgs };
                });
                saveConversations(updated);
                return updated;
              });
            }
          },
        );
      } catch (err) {
        setConversations((prev) => {
          const updated = prev.map((c) => {
            if (c.id !== convId) return c;
            const msgs = [...c.messages];
            const last = msgs[msgs.length - 1];
            // If streaming failed with no content yet, replace placeholder with error
            if (!last.content) {
              msgs[msgs.length - 1] = {
                ...last,
                content: `Sorry, something went wrong. ${err instanceof Error ? err.message : 'Please try again.'}`,
              };
            }
            return { ...c, messages: msgs };
          });
          saveConversations(updated);
          return updated;
        });
      } finally {
        // Persist final state and release loading lock
        setConversations((prev) => {
          saveConversations(prev);
          return prev;
        });
        setIsLoading(false);
      }
    },
    [activeId, actFilter, conversations, isLoading],
  );

  const pinConversation = useCallback((id: string) => {
    setConversations((prev) => {
      const updated = prev.map((c) => (c.id === id ? { ...c, pinned: !c.pinned } : c));
      saveConversations(updated);
      return updated;
    });
  }, []);

  const deleteConversation = useCallback(
    (id: string) => {
      setConversations((prev) => {
        const updated = prev.filter((c) => c.id !== id);
        saveConversations(updated);
        return updated;
      });
      if (activeId === id) {
        setActiveId(null);
        localStorage.removeItem(LS_ACTIVE);
      }
    },
    [activeId],
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
    pinConversation,
    deleteConversation,
  };
}

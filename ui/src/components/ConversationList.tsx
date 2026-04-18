'use client';

import { Pin, Trash2 } from 'lucide-react';
import type { StoredConversation } from '@/lib/chatStore';

interface Props {
  conversations: StoredConversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onPin: (id: string) => void;
  onDelete: (id: string) => void;
}

function dateLabel(ts: number): string {
  const d = new Date(ts);
  const now = new Date();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (d.toDateString() === now.toDateString()) return 'TODAY';
  if (d.toDateString() === yesterday.toDateString()) return 'YESTERDAY';
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase();
}

interface ConversationItemProps {
  conv: StoredConversation;
  isActive: boolean;
  onSelect: (id: string) => void;
  onPin: (id: string) => void;
  onDelete: (id: string) => void;
}

function ConversationItem({ conv, isActive, onSelect, onPin, onDelete }: ConversationItemProps) {
  return (
    <div
      className={`group relative flex items-center rounded-md transition-colors ${
        isActive ? 'bg-dark-elevated' : 'hover:bg-dark-elevated'
      }`}
    >
      <button
        onClick={() => onSelect(conv.id)}
        aria-current={isActive ? 'true' : undefined}
        className="flex-1 min-w-0 text-left px-3 py-2"
      >
        <p className={`text-xs font-sans truncate ${isActive ? 'text-ivory' : 'text-stone-gray group-hover:text-ivory'}`}>
          {conv.title}
        </p>
        <p className="text-[10px] font-sans text-olive-gray mt-0.5">
          {conv.actFilter ?? 'All acts'} · {conv.messages.length} msg
        </p>
      </button>

      {/* Action buttons — visible on hover or when active */}
      <div className={`flex items-center gap-0.5 pr-2 flex-shrink-0 transition-opacity ${
        isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
      }`}>
        <button
          onClick={(e) => { e.stopPropagation(); onPin(conv.id); }}
          title={conv.pinned ? 'Unpin' : 'Pin'}
          className={`p-1 rounded transition-colors ${
            conv.pinned
              ? 'text-terracotta hover:text-warm-silver'
              : 'text-stone-gray hover:text-warm-silver'
          }`}
        >
          <Pin className="w-3 h-3" />
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(conv.id); }}
          title="Delete"
          className="p-1 rounded text-stone-gray hover:text-red-400 transition-colors"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

export default function ConversationList({ conversations, activeId, onSelect, onPin, onDelete }: Props) {
  if (conversations.length === 0) {
    return (
      <p className="text-stone-gray text-xs font-sans px-3 py-4">No conversations yet.</p>
    );
  }

  const pinned = conversations.filter((c) => c.pinned);
  const unpinned = conversations.filter((c) => !c.pinned);

  // Group unpinned by date
  const groups: { label: string; items: StoredConversation[] }[] = [];
  for (const conv of unpinned) {
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
      {/* Pinned group */}
      {pinned.length > 0 && (
        <div>
          <p className="text-olive-gray text-[10px] font-sans tracking-[0.5px] px-3 py-1.5 mt-2">
            PINNED
          </p>
          {pinned.map((conv) => (
            <ConversationItem
              key={conv.id}
              conv={conv}
              isActive={conv.id === activeId}
              onSelect={onSelect}
              onPin={onPin}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}

      {/* Date-grouped unpinned */}
      {groups.map((group) => (
        <div key={group.label}>
          <p className="text-olive-gray text-[10px] font-sans tracking-[0.5px] px-3 py-1.5 mt-2">
            {group.label}
          </p>
          {group.items.map((conv) => (
            <ConversationItem
              key={conv.id}
              conv={conv}
              isActive={conv.id === activeId}
              onSelect={onSelect}
              onPin={onPin}
              onDelete={onDelete}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

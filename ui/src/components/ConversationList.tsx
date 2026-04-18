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
  const dStr = d.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (dStr === now.toDateString()) return 'TODAY';
  if (dStr === yesterday.toDateString()) return 'YESTERDAY';
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
                aria-current={isActive ? 'true' : undefined}
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

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

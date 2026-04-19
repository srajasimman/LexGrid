'use client';

import EmptyState from '@/components/EmptyState';
import MessageThread from '@/components/MessageThread';
import ChatInput from '@/components/ChatInput';
import type { StoredConversation } from '@/lib/chatStore';

interface Props {
  conversation: StoredConversation | null;
  isLoading: boolean;
  onSend: (query: string) => Promise<void>;
}

export default function ChatPanel({ conversation, isLoading, onSend }: Props) {
  const messages = conversation?.messages ?? [];
  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-col flex-1 min-h-0 bg-parchment">
      {/* Header */}
      <div className="hidden md:flex items-center justify-between px-5 py-3.5 bg-ivory border-b border-warm-sand flex-shrink-0">
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

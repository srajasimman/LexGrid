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
        <MessageBubble key={`${msg.timestamp}-${msg.role}`} message={msg} />
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

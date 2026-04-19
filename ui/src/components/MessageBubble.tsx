'use client';

import ReactMarkdown from 'react-markdown';
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
      <div className="hidden md:flex w-7 h-7 rounded-full bg-ink items-center justify-center flex-shrink-0 mt-0.5">
        <span className="text-xs">⚖️</span>
      </div>

      <div className="flex-1 min-w-0">
        {/* Answer */}
        <div className="bg-ivory border border-warm-sand rounded-[4px_16px_16px_16px] px-4 py-3 text-sm font-sans leading-[1.7] text-ink prose prose-sm max-w-none prose-p:my-1 prose-li:my-0 prose-headings:font-semibold prose-headings:text-ink prose-strong:text-ink">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Citations + perf chip */}
        {(message.citations && message.citations.length > 0) || message.latency_ms != null ? (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {message.citations?.map((c, i) => (
              <CitationBadge key={`${c.act_code}-${c.section_number}-${i}`} citation={c} />
            ))}
            {message.latency_ms != null && (
              <span className="text-stone-gray font-sans text-xs">
                {message.chunks_retrieved ?? '?'} sections
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

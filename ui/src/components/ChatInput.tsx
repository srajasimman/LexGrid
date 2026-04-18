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

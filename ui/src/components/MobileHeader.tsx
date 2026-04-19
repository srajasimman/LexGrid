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

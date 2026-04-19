'use client';

import { useState } from 'react';
import Sidebar from '@/components/Sidebar';
import ChatPanel from '@/components/ChatPanel';
import MobileHeader from '@/components/MobileHeader';
import { useChatStore } from '@/lib/chatStore';

export default function ChatShell() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

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
    pinConversation,
    deleteConversation,
  } = useChatStore();

  function handleSelectConversation(id: string) {
    selectConversation(id);
    setIsSidebarOpen(false);
  }

  function handleNewConversation() {
    newConversation();
    setIsSidebarOpen(false);
  }

  return (
    <div className="flex h-full">
      {/* Mobile backdrop */}
      <div
        className={`fixed inset-0 bg-black/50 z-40 md:hidden transition-opacity duration-200 ${
          isSidebarOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => setIsSidebarOpen(false)}
        aria-hidden="true"
      />

      {/* Sidebar — desktop: static; mobile: fixed slide-in overlay */}
      <div
        className={`
          fixed inset-y-0 left-0 z-50 transition-transform duration-200 ease-in-out
          md:static md:translate-x-0 md:z-auto md:transition-none
          ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <Sidebar
          conversations={conversations}
          activeId={activeId}
          actFilter={actFilter}
          onNewConversation={handleNewConversation}
          onSelectConversation={handleSelectConversation}
          onSetActFilter={setActFilter}
          onPinConversation={pinConversation}
          onDeleteConversation={deleteConversation}
          onClose={() => setIsSidebarOpen(false)}
        />
      </div>

      {/* Main area */}
      <div className="flex-1 min-w-0 flex flex-col">
        <MobileHeader
          title={activeConversation?.title ?? ''}
          onOpenSidebar={() => setIsSidebarOpen(true)}
          onNewConversation={handleNewConversation}
        />
        <ChatPanel
          conversation={activeConversation}
          isLoading={isLoading}
          onSend={sendMessage}
        />
      </div>
    </div>
  );
}

'use client';

import Sidebar from '@/components/Sidebar';
import ChatPanel from '@/components/ChatPanel';
import { useChatStore } from '@/lib/chatStore';

export default function ChatShell() {
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

  return (
    <div className="flex h-full">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        actFilter={actFilter}
        onNewConversation={newConversation}
        onSelectConversation={selectConversation}
        onSetActFilter={setActFilter}
        onPinConversation={pinConversation}
        onDeleteConversation={deleteConversation}
      />
      <div className="flex-1 min-w-0">
        <ChatPanel
          conversation={activeConversation}
          isLoading={isLoading}
          onSend={sendMessage}
        />
      </div>
    </div>
  );
}

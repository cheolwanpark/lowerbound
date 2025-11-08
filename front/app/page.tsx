"use client"

import { useState } from "react"
import { Sidebar } from "@/components/sidebar"
import { Chat } from "@/components/chat"
import { NewChatModal } from "@/components/new-chat-modal"
import { useChatList } from "@/hooks/use-chat-list"
import { useCreateChat } from "@/hooks/use-create-chat"
import { useToast } from "@/hooks/use-toast"
import { Toaster } from "@/components/ui/toaster"
import type { CreateChatParams } from "@/lib/types"

export default function Home() {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null)
  const [isNewChatModalOpen, setIsNewChatModalOpen] = useState(false)

  const { chats, isLoading: isLoadingChats, updateChatInList, refetch } = useChatList()
  const { create, isCreating } = useCreateChat()
  const { toast } = useToast()

  const handleCreateChat = async (params: CreateChatParams) => {
    const newChat = await create(params)

    if (newChat) {
      toast({
        title: "Chat created",
        description: "Your new chat has been created successfully",
      })
      setIsNewChatModalOpen(false)
      setSelectedChatId(newChat.id)
      // Refresh chat list to include the new chat
      refetch()
    } else {
      toast({
        title: "Error",
        description: "Failed to create chat. Please try again.",
        variant: "destructive",
      })
    }
  }

  return (
    <div className="dark flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar
        chats={chats}
        selectedChatId={selectedChatId}
        onSelectChat={setSelectedChatId}
        onNewChat={() => setIsNewChatModalOpen(true)}
        isLoading={isLoadingChats}
      />

      {/* Main Content */}
      <div className="flex flex-1 flex-col">
        {/* Chat Area */}
        <div className="flex-1 overflow-hidden">
          <Chat chatId={selectedChatId} onChatUpdate={updateChatInList} />
        </div>
      </div>

      {/* New Chat Modal */}
      <NewChatModal
        open={isNewChatModalOpen}
        onOpenChange={setIsNewChatModalOpen}
        onCreate={handleCreateChat}
        isCreating={isCreating}
      />

      {/* Toast Notifications */}
      <Toaster />
    </div>
  )
}

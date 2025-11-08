"use client"

import { useState, useEffect, useRef, useMemo } from "react"
import { Send, Loader2, MessageSquare } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { ChatBubble } from "@/components/chat-bubble"
import { ChatStatusBanner } from "@/components/chat-status-banner"
import { useChatDetail } from "@/hooks/use-chat-detail"
import { sendMessage } from "@/lib/api-client"
import { useToast } from "@/hooks/use-toast"
import type { BaseMessage, ChatListItem } from "@/lib/types"

interface ChatProps {
  chatId: string | null
  onChatUpdate?: (chatId: string, updates: Partial<ChatListItem>) => void
}

export function Chat({ chatId, onChatUpdate }: ChatProps) {
  const { chat, isLoading, error } = useChatDetail(chatId)
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const { toast } = useToast()

  // Update chat list when chat details change
  useEffect(() => {
    if (chat && onChatUpdate) {
      onChatUpdate(chat.id, {
        status: chat.status,
        message_count: chat.messages.length,
        has_portfolio: chat.portfolio !== null,
        updated_at: new Date().toISOString(),
      })
    }
  }, [chat?.status, chat?.messages.length, chat?.portfolio, chat?.id, onChatUpdate])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [chat?.messages.length])

  const handleSend = async () => {
    if (!input.trim() || !chatId || isSending) return

    const messageText = input.trim()
    setInput("")
    setIsSending(true)

    try {
      await sendMessage(chatId, messageText)
      // The polling hook will automatically fetch the updated chat
    } catch (err) {
      toast({
        title: "Error",
        description:
          err instanceof Error ? err.message : "Failed to send message",
        variant: "destructive",
      })
      // Restore the input on error
      setInput(messageText)
    } finally {
      setIsSending(false)
    }
  }

  // Empty state - no chat selected
  if (!chatId) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <MessageSquare className="mx-auto mb-4 h-12 w-12 text-muted-foreground/50" />
          <h3 className="mb-2 text-lg font-semibold">No chat selected</h3>
          <p className="text-sm text-muted-foreground">
            Select a chat from the sidebar or create a new one
          </p>
        </div>
      </div>
    )
  }

  // Loading state
  if (isLoading && !chat) {
    return (
      <div className="flex h-full flex-col p-6">
        <div className="mx-auto w-full max-w-3xl space-y-6">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-24 w-3/4" />
          <Skeleton className="ml-auto h-16 w-2/3" />
          <Skeleton className="h-32 w-3/4" />
        </div>
      </div>
    )
  }

  // Error state
  if (error || !chat) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h3 className="mb-2 text-lg font-semibold text-destructive">
            Error loading chat
          </h3>
          <p className="text-sm text-muted-foreground">
            {error?.message || "Chat not found"}
          </p>
        </div>
      </div>
    )
  }

  const canSendMessages = chat.status !== "completed" && chat.status !== "failed"

  // Create display messages with empty placeholder when processing
  const displayMessages = useMemo(() => {
    const messages = [...chat.messages]

    // If chat is processing and last message is from user (or no messages), add empty agent message
    if (chat.status === "processing") {
      const lastMessage = messages[messages.length - 1]
      if (!lastMessage || lastMessage.type === "user") {
        const emptyAgentMessage: BaseMessage = {
          type: "agent",
          message: "",
          timestamp: new Date().toISOString(),
          reasonings: [],
          toolcalls: [],
        }
        messages.push(emptyAgentMessage)
      }
    }

    return messages
  }, [chat.messages, chat.status])

  return (
    <div className="relative flex h-full flex-col">
      {/* Status Banner */}
      <div className="border-b border-border p-4">
        <div className="mx-auto max-w-3xl">
          <ChatStatusBanner
            status={chat.status}
            errorMessage={chat.error_message}
          />
        </div>
      </div>

      {/* Chat Messages */}
      <ScrollArea className="flex-1 p-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {displayMessages.length === 0 ? (
            <div className="flex h-full items-center justify-center py-12 text-center">
              <div>
                <MessageSquare className="mx-auto mb-4 h-12 w-12 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  No messages yet. Start the conversation!
                </p>
              </div>
            </div>
          ) : (
            <>
              {displayMessages.map((message, index) => (
                <ChatBubble
                  key={`${message.timestamp}-${index}`}
                  message={message}
                  chatStatus={chat.status}
                />
              ))}
              {/* Scroll anchor */}
              <div ref={scrollRef} />
            </>
          )}
        </div>
      </ScrollArea>

      {/* Input Area */}
      {canSendMessages && (
        <div className="border-t border-border bg-card p-4">
          <div className="mx-auto max-w-3xl">
            <div className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    handleSend()
                  }
                }}
                placeholder="메시지를 입력하세요..."
                className="rounded-xl"
                disabled={isSending}
              />
              <Button
                onClick={handleSend}
                size="icon"
                className="rounded-xl"
                disabled={isSending || !input.trim()}
              >
                {isSending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Disabled input area for completed/failed chats */}
      {!canSendMessages && (
        <div className="border-t border-border bg-muted/50 p-4">
          <div className="mx-auto max-w-3xl text-center text-sm text-muted-foreground">
            This chat is {chat.status}. You cannot send more messages.
          </div>
        </div>
      )}
    </div>
  )
}

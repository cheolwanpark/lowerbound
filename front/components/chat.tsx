"use client"

import { useState, useEffect, useRef, useMemo } from "react"
import { Send, Loader2, MessageSquare, ArrowDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { ChatBubble } from "@/components/chat-bubble"
import { ChatConfigStatus } from "@/components/chat-config-status"
import { ChatConfigPopup } from "@/components/chat-config-popup"
import { useChatDetail } from "@/hooks/use-chat-detail"
import { sendFollowup } from "@/lib/api-client"
import { toast } from "sonner"
import type { BaseMessage, ChatListItem, InvestmentStrategy } from "@/lib/types"

interface ChatProps {
  chatId: string | null
  onChatUpdate?: (chatId: string, updates: Partial<ChatListItem>) => void
}

export function Chat({ chatId, onChatUpdate }: ChatProps) {
  const { chat, isLoading, error, refetch } = useChatDetail(chatId)
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [showScrollButton, setShowScrollButton] = useState(false)
  const [configOverride, setConfigOverride] = useState<{
    strategy: InvestmentStrategy
    target_apy: number
    max_drawdown: number
  } | null>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  // Create display messages with empty placeholder when processing
  // Must be before any conditional returns to maintain hook order
  const displayMessages = useMemo(() => {
    if (!chat) return []

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
  }, [chat])

  // Update chat list when chat details change
  useEffect(() => {
    if (chat && onChatUpdate) {
      onChatUpdate(chat.id, {
        status: chat.status,
        message_count: chat.messages.length,
        has_portfolio: chat.portfolio !== null,
        updated_at: chat.updated_at, // Use server's timestamp, not client time
      })
    }
  }, [chat?.status, chat?.messages.length, chat?.portfolio, chat?.id, chat?.updated_at, onChatUpdate])

  // Check if user is near bottom of scroll area
  const isNearBottom = () => {
    if (!scrollAreaRef.current) return true
    const { scrollTop, scrollHeight, clientHeight } = scrollAreaRef.current
    const threshold = 100 // pixels from bottom
    return scrollHeight - scrollTop - clientHeight < threshold
  }

  // Handle scroll to update scroll button visibility
  const handleScroll = () => {
    const nearBottom = isNearBottom()
    setShowScrollButton(!nearBottom)
  }

  // Auto-scroll to bottom when new messages arrive (only if already at bottom)
  useEffect(() => {
    if (!scrollAreaRef.current) return

    if (isNearBottom()) {
      // Use setTimeout to ensure DOM has updated
      const scrollTimer = setTimeout(() => {
        if (scrollAreaRef.current) {
          scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
        }
      }, 0)

      return () => clearTimeout(scrollTimer)
    }
  }, [displayMessages.length])

  // Scroll to bottom function
  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTo({
        top: scrollAreaRef.current.scrollHeight,
        behavior: "smooth",
      })
    }
  }

  const handleSend = async () => {
    // Check if chat is already processing
    if (chat?.status === "processing" || chat?.status === "queued") {
      toast("Agent is processing your previous request. Please wait for it to complete before sending a new message.")
      return
    }

    if (!input.trim() || !chatId || isSending) return

    const messageText = input.trim()
    setInput("")
    setIsSending(true)

    try {
      await sendFollowup(chatId, messageText, configOverride || undefined)
      setConfigOverride(null) // Clear config override after sending
      // Force immediate refetch to show the user message
      await refetch()
    } catch (err) {
      toast("Failed to send message: " + (err instanceof Error ? err.message : "Unknown error"))
      // Restore the input on error
      setInput(messageText)
    } finally {
      setIsSending(false)
    }
  }

  const handleConfigChange = (config: {
    strategy: InvestmentStrategy
    target_apy: number
    max_drawdown: number
  }) => {
    setConfigOverride(config)
    toast("Configuration updated. These settings will be applied when you send your next message.")
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

  // Only block sending for failed chats (completed, timeout can receive followups)
  const canSendMessages = chat.status !== "failed"

  return (
    <div className="relative flex h-full flex-col">
      {/* Configuration Status Bar */}
      <ChatConfigStatus
        strategy={chat.strategy}
        targetApy={chat.target_apy}
        maxDrawdown={chat.max_drawdown}
      />

      {/* Chat Messages */}
      <div className="relative flex-1 overflow-hidden">
        <ScrollArea ref={scrollAreaRef} className="h-full">
          <div
            className="mx-auto w-full space-y-6 px-6 py-6"
            onScroll={handleScroll}
            style={{ maxWidth: '70vw' }}
          >
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
              displayMessages.map((message, index) => (
                <ChatBubble
                  key={`${message.timestamp}-${index}`}
                  message={message}
                  chatStatus={chat.status}
                />
              ))
            )}
          </div>
        </ScrollArea>

        {/* Scroll to bottom button */}
        {showScrollButton && (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
            <Button
              size="sm"
              variant="secondary"
              className="rounded-full shadow-lg"
              onClick={scrollToBottom}
            >
              <ArrowDown className="mr-2 h-4 w-4" />
              Scroll to bottom
            </Button>
          </div>
        )}
      </div>

      {/* Input Area */}
      {canSendMessages && (
        <div className="border-t border-border bg-card p-4">
          <div className="mx-auto w-full px-6" style={{ maxWidth: '70vw' }}>
            <div className="flex gap-2">
              <ChatConfigPopup
                currentStrategy={chat.strategy}
                currentApy={chat.target_apy}
                currentDrawdown={chat.max_drawdown}
                onConfigChange={handleConfigChange}
              />
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
                className="rounded-xl text-foreground"
                disabled={isSending || chat.status === "processing" || chat.status === "queued"}
              />
              <Button
                onClick={handleSend}
                size="icon"
                className="rounded-xl"
                disabled={isSending || !input.trim() || chat.status === "processing" || chat.status === "queued"}
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

      {/* Disabled input area for failed chats */}
      {!canSendMessages && (
        <div className="border-t border-border bg-muted/50 p-4">
          <div className="mx-auto w-full px-6 text-center text-sm text-muted-foreground" style={{ maxWidth: '70vw' }}>
            This chat has failed. You cannot send more messages.
          </div>
        </div>
      )}
    </div>
  )
}

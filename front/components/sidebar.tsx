"use client"

import { Plus, Sparkles, Loader2, CheckCircle2, XCircle, MessageSquare } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import type { ChatListItem } from "@/lib/types"

interface SidebarProps {
  chats: ChatListItem[]
  selectedChatId: string | null
  onSelectChat: (chatId: string) => void
  onNewChat: () => void
  isLoading?: boolean
}

function getStatusIcon(status: ChatListItem["status"]) {
  switch (status) {
    case "processing":
      return <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
    case "completed":
      return <CheckCircle2 className="h-3 w-3 text-green-500" />
    case "failed":
      return <XCircle className="h-3 w-3 text-red-500" />
  }
}

function getStrategyBadgeColor(strategy: ChatListItem["strategy"]) {
  switch (strategy) {
    case "Conservative":
      return "bg-blue-500/10 text-blue-500 border-blue-500/20"
    case "Balanced":
      return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20"
    case "Aggressive":
      return "bg-red-500/10 text-red-500 border-red-500/20"
  }
}

export function Sidebar({
  chats,
  selectedChatId,
  onSelectChat,
  onNewChat,
  isLoading = false,
}: SidebarProps) {
  // Sort chats by updated_at (most recent first)
  const sortedChats = [...chats].sort(
    (a, b) =>
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  )

  return (
    <div className="flex w-80 flex-col border-r border-border bg-sidebar">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-sidebar-border px-4 py-5">
        <Sparkles className="h-6 w-6 text-sidebar-primary" />
        <span className="text-lg font-semibold text-sidebar-foreground">
          Crypto Agent
        </span>
      </div>

      {/* New Chat Button */}
      <div className="border-b border-sidebar-border p-3">
        <Button
          variant="outline"
          className="w-full justify-start rounded-xl bg-transparent"
          onClick={onNewChat}
        >
          <Plus className="mr-2 h-4 w-4" />
          New Chat
        </Button>
      </div>

      {/* Chat List */}
      <ScrollArea className="flex-1 px-3 py-4">
        {isLoading && chats.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Loading chats...
          </div>
        ) : sortedChats.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <MessageSquare className="mb-2 h-8 w-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">No chats yet</p>
            <p className="mt-1 text-xs text-muted-foreground/70">
              Click "New Chat" to get started
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {sortedChats.map((chat) => {
              const updatedAt = new Date(chat.updated_at)
              const isToday =
                updatedAt.toDateString() === new Date().toDateString()
              const timeString = isToday
                ? updatedAt.toLocaleTimeString("ko-KR", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : updatedAt.toLocaleDateString("ko-KR", {
                    month: "short",
                    day: "numeric",
                  })

              return (
                <button
                  key={chat.id}
                  onClick={() => onSelectChat(chat.id)}
                  className={cn(
                    "w-full rounded-xl px-3 py-3 text-left transition-colors",
                    selectedChatId === chat.id
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent/50",
                  )}
                >
                  {/* Header row: Strategy + Status */}
                  <div className="mb-1.5 flex items-center justify-between gap-2">
                    <Badge
                      variant="outline"
                      className={cn(
                        "h-5 border px-2 text-[10px] font-medium",
                        getStrategyBadgeColor(chat.strategy),
                      )}
                    >
                      {chat.strategy}
                    </Badge>
                    <div className="flex items-center gap-1">
                      {getStatusIcon(chat.status)}
                    </div>
                  </div>

                  {/* Targets */}
                  <div className="mb-1.5 flex items-center gap-2 text-xs text-muted-foreground">
                    <span>APY: {chat.target_apy}%</span>
                    <span>·</span>
                    <span>DD: {chat.max_drawdown}%</span>
                  </div>

                  {/* Footer row: Message count + Time */}
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <MessageSquare className="h-3 w-3" />
                      <span>{chat.message_count}</span>
                    </div>
                    <span>{timeString}</span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}

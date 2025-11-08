"use client"

import { MessageCircle } from "lucide-react"
import type { Message } from "@/types"
import { format } from "date-fns"
import { ko } from "date-fns/locale"

interface ChatHistoryProps {
  messages: Message[]
  portfolioName?: string
  riskProfile: string
  targetReturn: number
  maxDrawdown: number
  selectedMessageId?: string
  onSelectMessage?: (messageId: string) => void
}

export default function ChatHistory({
  messages,
  portfolioName,
  riskProfile,
  targetReturn,
  maxDrawdown,
  selectedMessageId,
  onSelectMessage,
}: ChatHistoryProps) {
  return (
    <div className="w-auto flex-grow basis-2/7 bg-gradient-to-b from-card to-background border-r border-border flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-4 border-b border-border">
        <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
          <MessageCircle className="w-4 h-4" />
          Chat History
        </h2>
        {portfolioName && <p className="text-xs text-muted-foreground mt-2">{portfolioName}</p>}
      </div>

      {/* Settings Summary */}
      <div className="px-4 py-3 border-b border-border bg-muted/30">
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="text-muted-foreground">Risk:</span>
            <span className="font-medium text-foreground">{riskProfile}</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-muted-foreground">Return:</span>
            <span className="font-medium text-foreground">{targetReturn}%</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-muted-foreground">Drawdown:</span>
            <span className="font-medium text-foreground">{maxDrawdown}%</span>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-center">
            <div>
              <MessageCircle className="w-8 h-8 text-muted-foreground/40 mx-auto mb-2" />
              <p className="text-xs text-muted-foreground">No messages yet</p>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <button
              key={msg.id}
              onClick={() => onSelectMessage?.(msg.id)}
              className={`w-full text-left text-xs p-2.5 rounded-lg transition-all ${
                selectedMessageId === msg.id
                  ? msg.type === "user"
                    ? "bg-primary/20 text-foreground border border-primary shadow-sm"
                    : "bg-primary/15 text-foreground border border-primary shadow-sm"
                  : msg.type === "user"
                    ? "bg-primary/10 text-foreground border border-primary/20 hover:bg-primary/15"
                    : "bg-muted/50 text-muted-foreground border border-border hover:bg-muted/70"
              }`}
            >
              <div className="font-medium mb-1 text-xs">{msg.type === "user" ? "You" : "AI"}</div>
              <p className="line-clamp-2 text-xs opacity-80">{msg.content || "Portfolio Analysis"}</p>
              <div className="text-xs opacity-50 mt-1">{format(msg.timestamp, "HH:mm", { locale: ko })}</div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}

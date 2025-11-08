"use client"

import { useState, useMemo } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronUp, Sparkles, Wrench } from "lucide-react"
import { ThinkingIndicator } from "@/components/thinking-indicator"
import { ToolCallModal } from "@/components/tool-call-modal"
import type { BaseMessage, Reasoning, ToolCall, ChatStatus } from "@/lib/types"

interface ChatBubbleProps {
  message: BaseMessage
  chatStatus?: ChatStatus
}

// Timeline item type for sorting reasonings and tool calls by timestamp
interface TimelineItem {
  type: "reasoning" | "toolcall"
  timestamp: string
  data: Reasoning | ToolCall
}

export function ChatBubble({ message, chatStatus }: ChatBubbleProps) {
  const [showReasoning, setShowReasoning] = useState(false)
  const [selectedToolCall, setSelectedToolCall] = useState<ToolCall | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const timestamp = new Date(message.timestamp)

  // User message - simple bubble
  if (message.type === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%]">
          <div className="rounded-2xl bg-primary px-4 py-3 text-sm text-primary-foreground">
            {message.message}
          </div>
          <div className="mt-1 text-right text-xs text-muted-foreground">
            {timestamp.toLocaleTimeString("ko-KR")}
          </div>
        </div>
      </div>
    )
  }

  // Combine reasonings and tool calls into a timeline, sorted by timestamp
  const timeline = useMemo(() => {
    const items: TimelineItem[] = []

    message.reasonings.forEach((reasoning) => {
      items.push({
        type: "reasoning",
        timestamp: reasoning.timestamp,
        data: reasoning,
      })
    })

    message.toolcalls.forEach((toolcall) => {
      items.push({
        type: "toolcall",
        timestamp: toolcall.timestamp,
        data: toolcall,
      })
    })

    // Sort by timestamp
    items.sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    )

    return items
  }, [message.reasonings, message.toolcalls])

  const hasReasoningDetails = timeline.length > 0
  const isProcessing = chatStatus === "processing"
  const isEmptyMessage = !message.message || message.message.trim() === ""

  const handleToolCallClick = (toolCall: ToolCall) => {
    setSelectedToolCall(toolCall)
    setIsModalOpen(true)
  }

  // Agent message
  return (
    <div className="flex justify-start">
      <div className="w-full max-w-[85%]">
        <Card className="overflow-hidden rounded-xl border-border">
          {/* Agent Response */}
          {message.message && message.message !== "[Agent is thinking...]" && (
            <div className="p-4">
              <p className="whitespace-pre-wrap text-sm">{message.message}</p>
            </div>
          )}

          {/* Show Reasoning Button */}
          {hasReasoningDetails && (
            <div className="border-t border-border px-4 py-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowReasoning(!showReasoning)}
                className="h-auto w-full justify-between p-2 text-xs text-muted-foreground hover:bg-muted/50"
              >
                <span>Show Reasoning</span>
                {showReasoning ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </Button>

              {/* Reasoning Details (Dropdown) */}
              {showReasoning && (
                <div className="mt-2 space-y-3 border-t border-border pt-3">
                  {timeline.map((item, index) => {
                    if (item.type === "reasoning") {
                      const reasoning = item.data as Reasoning
                      return (
                        <div key={`reasoning-${index}`} className="space-y-1">
                          <div className="flex items-start gap-2">
                            <Sparkles className="mt-0.5 h-3 w-3 flex-shrink-0 text-primary" />
                            <div className="flex-1 space-y-1">
                              <p className="text-xs font-semibold">
                                {reasoning.summary}
                              </p>
                              <p className="whitespace-pre-wrap text-xs text-muted-foreground">
                                {reasoning.detail}
                              </p>
                              <p className="text-[10px] text-muted-foreground/70">
                                {new Date(reasoning.timestamp).toLocaleTimeString("ko-KR")}
                              </p>
                            </div>
                          </div>
                        </div>
                      )
                    } else {
                      const toolcall = item.data as ToolCall
                      return (
                        <div key={`toolcall-${index}`} className="space-y-1">
                          <div className="flex items-start gap-2">
                            <Wrench className="mt-0.5 h-3 w-3 flex-shrink-0 text-blue-500" />
                            <div className="flex-1 space-y-1">
                              <button
                                onClick={() => handleToolCallClick(toolcall)}
                                className="text-left text-xs text-blue-500 hover:underline"
                              >
                                {toolcall.message}
                              </button>
                              <p className="text-[10px] text-muted-foreground/70">
                                {new Date(toolcall.timestamp).toLocaleTimeString("ko-KR")}
                              </p>
                            </div>
                          </div>
                        </div>
                      )
                    }
                  })}
                </div>
              )}
            </div>
          )}

          {/* Thinking Indicator (when processing or message is empty) */}
          {(isProcessing || isEmptyMessage) && <ThinkingIndicator />}

          {/* Timestamp */}
          {!isProcessing && !isEmptyMessage && (
            <div className="border-t border-border px-4 py-2">
              <p className="text-xs text-muted-foreground">
                {timestamp.toLocaleTimeString("ko-KR")}
              </p>
            </div>
          )}
        </Card>

        {/* Tool Call Modal */}
        <ToolCallModal
          toolCall={selectedToolCall}
          open={isModalOpen}
          onOpenChange={setIsModalOpen}
        />
      </div>
    </div>
  )
}

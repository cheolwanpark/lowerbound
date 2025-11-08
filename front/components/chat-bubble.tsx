"use client"

import { useState, useMemo } from "react"
import { ChevronDown, ChevronUp, Sparkles, Wrench } from "lucide-react"
import Markdown, { Components } from "react-markdown"
import remarkGfm from "remark-gfm"
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

  // Custom markdown components with proper styling
  const markdownComponents: Components = {
    p: ({ children }) => (
      <p className="mb-3 last:mb-0 text-card-foreground">{children}</p>
    ),
    h1: ({ children }) => (
      <h1 className="mb-3 mt-4 text-2xl font-bold text-card-foreground">{children}</h1>
    ),
    h2: ({ children }) => (
      <h2 className="mb-3 mt-4 text-xl font-bold text-card-foreground">{children}</h2>
    ),
    h3: ({ children }) => (
      <h3 className="mb-2 mt-3 text-lg font-bold text-card-foreground">{children}</h3>
    ),
    code: ({ inline, className, children, ...props }: any) => {
      return inline ? (
        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-sm text-card-foreground" {...props}>
          {children}
        </code>
      ) : (
        <code className="block overflow-x-auto rounded-lg border border-border bg-muted p-3 font-mono text-sm text-card-foreground" {...props}>
          {children}
        </code>
      )
    },
    pre: ({ children }) => (
      <pre className="my-3 overflow-x-auto rounded-lg border border-border bg-muted p-3">
        {children}
      </pre>
    ),
    a: ({ href, children }) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-blue-500 underline hover:text-blue-600"
      >
        {children}
      </a>
    ),
    ul: ({ children }) => (
      <ul className="my-3 ml-6 list-disc text-card-foreground">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="my-3 ml-6 list-decimal text-card-foreground">{children}</ol>
    ),
    li: ({ children }) => <li className="mb-1">{children}</li>,
    blockquote: ({ children }) => (
      <blockquote className="my-3 border-l-4 border-border pl-4 italic text-card-foreground/80">
        {children}
      </blockquote>
    ),
    table: ({ children }) => (
      <div className="my-3 overflow-x-auto">
        <table className="min-w-full border-collapse border border-border">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="bg-muted">{children}</thead>
    ),
    th: ({ children }) => (
      <th className="border border-border px-4 py-2 text-left font-semibold text-card-foreground">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="border border-border px-4 py-2 text-card-foreground">
        {children}
      </td>
    ),
    strong: ({ children }) => (
      <strong className="font-bold text-card-foreground">{children}</strong>
    ),
    em: ({ children }) => (
      <em className="italic text-card-foreground">{children}</em>
    ),
    hr: () => <hr className="my-4 border-t border-border" />,
  }

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
  const isEmptyMessage = !message.message ||
                         message.message.trim() === "" ||
                         message.message === "[Agent is thinking...]"

  const handleToolCallClick = (toolCall: ToolCall) => {
    setSelectedToolCall(toolCall)
    setIsModalOpen(true)
  }

  // Agent message
  return (
    <div className="flex justify-start">
      <div className="w-full max-w-[70%]">
        <div className="overflow-hidden rounded-2xl border border-border bg-card text-card-foreground">
          {/* Show Reasoning Button - At the top, seamless */}
          {hasReasoningDetails && (
            <>
              <div className="px-4 pb-2 pt-3">
                <button
                  onClick={() => setShowReasoning(!showReasoning)}
                  className="inline-flex items-center gap-1 text-xs text-card-foreground/70 transition-colors hover:text-card-foreground"
                >
                  <span>Show reasoning</span>
                  {showReasoning ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                </button>
              </div>

              {/* Reasoning Details (Dropdown) */}
              {showReasoning && (
                <div className="space-y-3 border-b border-border px-4 pb-3 pt-2">
                  {timeline.map((item, index) => {
                    if (item.type === "reasoning") {
                      const reasoning = item.data as Reasoning
                      return (
                        <div key={`reasoning-${index}`} className="space-y-1">
                          <div className="flex items-start gap-2">
                            <Sparkles className="mt-0.5 h-3 w-3 flex-shrink-0 text-primary" />
                            <div className="flex-1 space-y-1">
                              <div className="text-xs font-semibold text-card-foreground">
                                <Markdown
                                  remarkPlugins={[remarkGfm]}
                                  components={markdownComponents}
                                  skipHtml
                                >
                                  {reasoning.summary}
                                </Markdown>
                              </div>
                              <div className="text-xs text-card-foreground/80">
                                <Markdown
                                  remarkPlugins={[remarkGfm]}
                                  components={markdownComponents}
                                  skipHtml
                                >
                                  {reasoning.detail}
                                </Markdown>
                              </div>
                              <p className="text-[10px] text-card-foreground/60">
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
                              <p className="text-[10px] text-card-foreground/60">
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
            </>
          )}

          {/* Agent Response */}
          {message.message && message.message !== "[Agent is thinking...]" && (
            <div className="prose prose-sm max-w-none px-4 py-3">
              <Markdown
                remarkPlugins={[remarkGfm]}
                components={markdownComponents}
                skipHtml
              >
                {message.message}
              </Markdown>
            </div>
          )}

          {/* Progress Preview - Show last 3 items when message is empty (actively generating) and reasoning is not expanded */}
          {isEmptyMessage && hasReasoningDetails && !showReasoning && (
            <div className="space-y-2 border-t border-border px-4 py-3">
              <p className="text-xs text-card-foreground/60">Recent activity:</p>
              {timeline.slice(-3).map((item, index) => {
                if (item.type === "reasoning") {
                  const reasoning = item.data as Reasoning
                  return (
                    <div key={`preview-reasoning-${index}`} className="flex items-start gap-2">
                      <Sparkles className="mt-0.5 h-3 w-3 flex-shrink-0 text-primary" />
                      <p className="text-xs text-card-foreground/80">
                        {reasoning.summary}
                      </p>
                    </div>
                  )
                } else {
                  const toolcall = item.data as ToolCall
                  return (
                    <div key={`preview-toolcall-${index}`} className="flex items-start gap-2">
                      <Wrench className="mt-0.5 h-3 w-3 flex-shrink-0 text-blue-500" />
                      <p className="text-xs text-card-foreground/80">
                        {toolcall.message}
                      </p>
                    </div>
                  )
                }
              })}
            </div>
          )}

          {/* Thinking Indicator (when message is empty - actively generating) */}
          {isEmptyMessage && <ThinkingIndicator />}
        </div>

        {/* Timestamp - Outside the box */}
        {!isProcessing && !isEmptyMessage && (
          <div className="mt-1 text-xs text-muted-foreground">
            {timestamp.toLocaleTimeString("ko-KR")}
          </div>
        )}

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

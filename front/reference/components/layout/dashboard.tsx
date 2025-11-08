"use client"

import { useRef, useEffect } from "react"
import ChatInterface from "@/components/chat/chat-interface"
import ChatMessages from "@/components/chat/chat-messages"
import type { Portfolio, Message } from "@/types"
import { Settings } from "lucide-react"

interface DashboardProps {
  portfolio: Portfolio | undefined
  messages: Message[]
  onSendMessage: (message: string) => void
  riskProfile: "Passive" | "Conservative" | "Aggressive"
  targetReturn: number
  maxDrawdown: number
  onRiskProfileChange: (value: "Passive" | "Conservative" | "Aggressive") => void
  onTargetReturnChange: (value: number) => void
  onMaxDrawdownChange: (value: number) => void
  selectedMessageId?: string
  settingsExpanded: boolean
  onSettingsExpandedChange: (expanded: boolean) => void
}

export default function Dashboard({
  portfolio,
  messages,
  onSendMessage,
  riskProfile,
  targetReturn,
  maxDrawdown,
  onRiskProfileChange,
  onTargetReturnChange,
  onMaxDrawdownChange,
  selectedMessageId,
  settingsExpanded,
  onSettingsExpandedChange,
}: DashboardProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  return (
    <div className="flex-grow basis-5/7 flex flex-col bg-background">
      {/* Header */}
      <div className="border-b border-border px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{portfolio?.name || "Portfolio"}</h1>
          <p className="text-sm text-muted-foreground mt-1">AI-powered derivative portfolio design</p>
        </div>
        <Settings className="w-5 h-5 text-muted-foreground" />
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        <ChatMessages
          messages={messages}
          riskProfile={riskProfile}
          targetReturn={targetReturn}
          maxDrawdown={maxDrawdown}
          selectedMessageId={selectedMessageId}
        />
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-border p-6 bg-background">
        <ChatInterface
          onSendMessage={onSendMessage}
          riskProfile={riskProfile}
          targetReturn={targetReturn}
          maxDrawdown={maxDrawdown}
          onRiskProfileChange={onRiskProfileChange}
          onTargetReturnChange={onTargetReturnChange}
          onMaxDrawdownChange={onMaxDrawdownChange}
          showSettings={settingsExpanded}
          onShowSettingsChange={onSettingsExpandedChange}
        />
      </div>
    </div>
  )
}

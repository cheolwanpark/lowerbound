"use client"

import PortfolioResponse from "./portfolio-response"
import type { Message } from "@/types"
import { Sparkles } from "lucide-react"

interface ChatMessagesProps {
  messages: Message[]
  riskProfile: "Passive" | "Conservative" | "Aggressive"
  targetReturn: number
  maxDrawdown: number
  selectedMessageId?: string
}

export default function ChatMessages({
  messages,
  riskProfile,
  targetReturn,
  maxDrawdown,
  selectedMessageId,
}: ChatMessagesProps) {
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-primary/10 rounded-lg">
              <Sparkles className="w-6 h-6 text-primary" />
            </div>
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-2">Crypto Derivative Portfolio Designer</h2>
          <p className="text-muted-foreground leading-relaxed">
            설정을 입력하고 질문을 하면 AI가 당신의 포트폴리오를 설계해줍니다.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4 p-6">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`transition-all ${msg.type === "assistant" && selectedMessageId === msg.id ? "opacity-100" : ""}`}
        >
          {msg.type === "user" ? (
            <div className="flex justify-end">
              <div className="max-w-md bg-primary text-primary-foreground rounded-lg px-4 py-2.5 shadow-sm">
                <p className="text-sm">{msg.content}</p>
              </div>
            </div>
          ) : msg.isPortfolioResponse ? (
            <div
              className={`transition-all rounded-lg ${
                selectedMessageId === msg.id ? "ring-2 ring-amber-400 p-4 bg-amber-50/20" : ""
              }`}
            >
              <PortfolioResponse riskProfile={riskProfile} targetReturn={targetReturn} maxDrawdown={maxDrawdown} />
            </div>
          ) : (
            <div className="flex justify-start">
              <div className="max-w-2xl bg-muted/30 border border-border rounded-lg px-4 py-2.5">
                <p className="text-sm text-foreground">{msg.content}</p>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

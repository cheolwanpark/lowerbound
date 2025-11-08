"use client"

import { useState } from "react"
import { Send, ChevronUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { PresetForm } from "@/components/preset-form"
import { ChatBubble } from "@/components/chat-bubble"
import { PortfolioVersionTag } from "@/components/portfolio-version-tag"

interface ChatProps {
  projectId: string
}

const mockMessages = [
  {
    id: "1",
    role: "user",
    content: "보수적인 전략으로 포트폴리오를 생성해줘",
    timestamp: new Date("2025-01-10T10:00:00"),
  },
  {
    id: "2",
    role: "assistant",
    content: {
      reasoning: `1. 사용자가 보수적인 전략을 요청했으므로 안정적인 자산 비중을 높입니다.
2. BTC와 ETH를 중심으로 포트폴리오를 구성합니다.
3. USDC 스테이블코인을 20% 포함하여 변동성을 낮춥니다.
4. 예상 APY는 8-10%, 최대 낙폭은 15% 이하로 설정합니다.`,
      allocation: [
        { asset: "BTC", percentage: 40 },
        { asset: "ETH", percentage: 30 },
        { asset: "SOL", percentage: 10 },
        { asset: "USDC", percentage: 20 },
      ],
      risk: "Low",
      apy: 9.2,
      drawdown: 12.5,
    },
    timestamp: new Date("2025-01-10T10:00:30"),
    version: "v1",
  },
  {
    id: "3",
    role: "user",
    content: "APY를 12%로 올려줘",
    timestamp: new Date("2025-01-10T10:05:00"),
  },
  {
    id: "4",
    role: "assistant",
    content: {
      reasoning: `1. 목표 APY를 12%로 상향 조정하기 위해 고수익 자산 비중을 증가시킵니다.
2. SOL 비중을 15%로 증가시킵니다.
3. USDC 비중을 15%로 감소시킵니다.
4. 이에 따라 리스크가 Medium으로 상승합니다.`,
      allocation: [
        { asset: "BTC", percentage: 40 },
        { asset: "ETH", percentage: 30 },
        { asset: "SOL", percentage: 15 },
        { asset: "USDC", percentage: 15 },
      ],
      risk: "Medium",
      apy: 12.1,
      drawdown: 16.8,
    },
    timestamp: new Date("2025-01-10T10:05:30"),
    version: "v2",
  },
]

export function Chat({ projectId }: ChatProps) {
  const [messages] = useState(mockMessages)
  const [input, setInput] = useState("")
  const [showPreset, setShowPreset] = useState(false)

  const handleSend = () => {
    if (!input.trim()) return
    // Mock send functionality
    setInput("")
  }

  return (
    <div className="relative flex h-full flex-col">
      {/* Chat Messages */}
      <ScrollArea className="flex-1 p-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.map((message) => (
            <div key={message.id}>
              <ChatBubble message={message} />
              {message.role === "assistant" && message.version && <PortfolioVersionTag version={message.version} />}
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="border-t border-border bg-card p-4">
        <div className="mx-auto max-w-3xl">
          <div className="mb-2 flex justify-end">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowPreset(!showPreset)}
              className="text-xs text-muted-foreground"
            >
              Portfolio Preset
              <ChevronUp className={`ml-1 h-3 w-3 transition-transform ${showPreset ? "" : "rotate-180"}`} />
            </Button>
          </div>
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
            />
            <Button onClick={handleSend} size="icon" className="rounded-xl">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Preset Form Drawer */}
      {showPreset && (
        <div className="border-t border-border bg-card p-6">
          <div className="mx-auto max-w-3xl">
            <PresetForm />
          </div>
        </div>
      )}
    </div>
  )
}

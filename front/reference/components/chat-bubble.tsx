"use client"

import { useState } from "react"
import { Sparkles, ChevronDown, ChevronUp } from "lucide-react"
import { Card } from "@/components/ui/card"

interface Message {
  id: string
  role: "user" | "assistant"
  content:
    | string
    | {
        reasoning: string
        allocation: Array<{ asset: string; percentage: number }>
        risk: string
        apy: number
        drawdown: number
      }
  timestamp: Date
  version?: string
}

interface ChatBubbleProps {
  message: Message
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const [showReasoning, setShowReasoning] = useState(true)

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%]">
          <div className="rounded-2xl bg-primary px-4 py-3 text-sm text-primary-foreground">
            {message.content as string}
          </div>
          <div className="mt-1 text-right text-xs text-muted-foreground">
            {message.timestamp.toLocaleTimeString("ko-KR")}
          </div>
        </div>
      </div>
    )
  }

  const content = message.content as {
    reasoning: string
    allocation: Array<{ asset: string; percentage: number }>
    risk: string
    apy: number
    drawdown: number
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[70%] space-y-3">
        {/* Reasoning */}
        <Card className="rounded-xl border-border">
          <div className="relative">
            <div className="absolute left-3 top-3 flex h-5 w-5 items-center justify-center rounded-md bg-primary/10">
              <Sparkles className="h-3 w-3 text-primary" />
            </div>
            <button
              onClick={() => setShowReasoning(!showReasoning)}
              className="flex w-full items-center justify-between p-4 pl-11 text-left"
            >
              <span className="text-sm font-medium">Reasoning</span>
              {showReasoning ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
            {showReasoning && (
              <div className="border-t border-border px-4 py-3 text-xs leading-relaxed text-muted-foreground whitespace-pre-line">
                {content.reasoning}
              </div>
            )}
          </div>
        </Card>

        {/* Final Output */}
        <Card className="rounded-xl border-border">
          <div className="relative p-4">
            <div className="absolute left-3 top-3 flex h-5 w-5 items-center justify-center rounded-md bg-primary/10">
              <Sparkles className="h-3 w-3 text-primary" />
            </div>
            <h4 className="mb-3 pl-8 text-sm font-semibold">Final Output</h4>

            {/* Portfolio Allocation Table */}
            <div className="mb-4 overflow-hidden rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Asset</th>
                    <th className="px-3 py-2 text-right font-medium">Allocation</th>
                  </tr>
                </thead>
                <tbody>
                  {content.allocation.map((item) => (
                    <tr key={item.asset} className="border-t border-border">
                      <td className="px-3 py-2">{item.asset}</td>
                      <td className="px-3 py-2 text-right font-mono">{item.percentage}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Risk Overview */}
            <div className="space-y-2 rounded-lg bg-muted/50 p-3 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Risk Level:</span>
                <span className="font-medium">{content.risk}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Expected APY:</span>
                <span className="font-medium text-green-500">{content.apy}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Max Drawdown:</span>
                <span className="font-medium text-red-500">{content.drawdown}%</span>
              </div>
            </div>
          </div>
        </Card>

        <div className="text-xs text-muted-foreground">{message.timestamp.toLocaleTimeString("ko-KR")}</div>
      </div>
    </div>
  )
}

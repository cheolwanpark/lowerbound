"use client"

import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import type { InvestmentStrategy } from "@/lib/types"

interface ChatConfigStatusProps {
  strategy: InvestmentStrategy
  targetApy: number
  maxDrawdown: number
}

function getStrategyColor(strategy: InvestmentStrategy): string {
  switch (strategy) {
    case "Passive":
      return "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/20"
    case "Conservative":
      return "bg-green-500/10 text-green-700 dark:text-green-300 border-green-500/20"
    case "Aggressive":
      return "bg-red-500/10 text-red-700 dark:text-red-300 border-red-500/20"
    default:
      return "bg-gray-500/10 text-gray-700 dark:text-gray-300 border-gray-500/20"
  }
}

export function ChatConfigStatus({
  strategy,
  targetApy,
  maxDrawdown,
}: ChatConfigStatusProps) {
  return (
    <div className="border-b border-border bg-card px-6 py-2.5">
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Strategy:</span>
          <Badge variant="outline" className={getStrategyColor(strategy)}>
            {strategy}
          </Badge>
        </div>
        <Separator orientation="vertical" className="h-4" />
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Target APY:</span>
          <span className="font-medium text-foreground">{targetApy}%</span>
        </div>
        <Separator orientation="vertical" className="h-4" />
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Max Drawdown:</span>
          <span className="font-medium text-foreground">{maxDrawdown}%</span>
        </div>
      </div>
    </div>
  )
}

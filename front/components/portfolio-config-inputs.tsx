"use client"

import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import type { InvestmentStrategy } from "@/lib/types"
import { clampAPY, clampDrawdown } from "@/lib/types"

interface PortfolioConfigInputsProps {
  strategy: InvestmentStrategy
  targetAPY: string
  maxDrawdown: string
  onStrategyChange: (value: InvestmentStrategy) => void
  onTargetAPYChange: (value: string) => void
  onMaxDrawdownChange: (value: string) => void
  compact?: boolean
}

export function PortfolioConfigInputs({
  strategy,
  targetAPY,
  maxDrawdown,
  onStrategyChange,
  onTargetAPYChange,
  onMaxDrawdownChange,
  compact = false,
}: PortfolioConfigInputsProps) {
  // Auto-clamp values on blur
  const handleAPYBlur = () => {
    const numValue = parseFloat(targetAPY) || 0
    const clamped = clampAPY(numValue)
    if (clamped !== numValue) {
      onTargetAPYChange(String(clamped))
    }
  }

  const handleDrawdownBlur = () => {
    const numValue = parseFloat(maxDrawdown) || 0
    const clamped = clampDrawdown(numValue)
    if (clamped !== numValue) {
      onMaxDrawdownChange(String(clamped))
    }
  }

  return (
    <div className={compact ? "flex gap-2" : "grid gap-4 sm:grid-cols-3"}>
      <div className="space-y-2">
        <Label htmlFor="strategy">Investment Strategy</Label>
        <Select
          value={strategy}
          onValueChange={(value) => onStrategyChange(value as InvestmentStrategy)}
        >
          <SelectTrigger id="strategy" className="rounded-lg">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="Passive">Passive</SelectItem>
            <SelectItem value="Conservative">Conservative</SelectItem>
            <SelectItem value="Aggressive">Aggressive</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="apy">Target APY (%)</Label>
        <Input
          id="apy"
          type="number"
          min="0"
          max="200"
          step="0.1"
          value={targetAPY}
          onChange={(e) => onTargetAPYChange(e.target.value)}
          onBlur={handleAPYBlur}
          className="rounded-lg"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="drawdown">Maximum Drawdown (%)</Label>
        <Input
          id="drawdown"
          type="number"
          min="0"
          max="100"
          step="0.1"
          value={maxDrawdown}
          onChange={(e) => onMaxDrawdownChange(e.target.value)}
          onBlur={handleDrawdownBlur}
          className="rounded-lg"
          required
        />
      </div>
    </div>
  )
}

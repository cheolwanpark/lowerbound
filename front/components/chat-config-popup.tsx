"use client"

import { useState, useEffect } from "react"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Button } from "@/components/ui/button"
import { Settings } from "lucide-react"
import type { InvestmentStrategy } from "@/lib/types"
import { PortfolioConfigInputs } from "./portfolio-config-inputs"

interface ChatConfigPopupProps {
  currentStrategy: InvestmentStrategy
  currentApy: number
  currentDrawdown: number
  onConfigChange: (config: {
    strategy: InvestmentStrategy
    target_apy: number
    max_drawdown: number
  }) => void
}

export function ChatConfigPopup({
  currentStrategy,
  currentApy,
  currentDrawdown,
  onConfigChange,
}: ChatConfigPopupProps) {
  const [open, setOpen] = useState(false)
  const [strategy, setStrategy] = useState(currentStrategy)
  const [apy, setApy] = useState(String(currentApy))
  const [drawdown, setDrawdown] = useState(String(currentDrawdown))

  // Reset to backend values when popup opens
  useEffect(() => {
    if (open) {
      setStrategy(currentStrategy)
      setApy(String(currentApy))
      setDrawdown(String(currentDrawdown))
    }
  }, [open, currentStrategy, currentApy, currentDrawdown])

  const handleApply = () => {
    onConfigChange({
      strategy,
      target_apy: parseFloat(apy),
      max_drawdown: parseFloat(drawdown),
    })
    setOpen(false)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="icon" title="Configure portfolio parameters" className="text-foreground">
          <Settings className="h-4 w-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent side="top" align="start" className="w-[600px]">
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold">Portfolio Configuration</h4>
            <p className="text-xs text-muted-foreground mt-1">
              Changes will be applied to your next message
            </p>
          </div>

          <PortfolioConfigInputs
            strategy={strategy}
            targetAPY={apy}
            maxDrawdown={drawdown}
            onStrategyChange={setStrategy}
            onTargetAPYChange={setApy}
            onMaxDrawdownChange={setDrawdown}
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleApply}>
              Apply Configuration
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}

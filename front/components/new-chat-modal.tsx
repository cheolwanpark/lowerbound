"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Loader2 } from "lucide-react"
import type { InvestmentStrategy } from "@/lib/types"

interface NewChatModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreate: (params: {
    strategy: InvestmentStrategy
    target_apy: number
    max_drawdown: number
    initial_message: string
  }) => void
  isCreating?: boolean
}

export function NewChatModal({
  open,
  onOpenChange,
  onCreate,
  isCreating = false,
}: NewChatModalProps) {
  const [strategy, setStrategy] = useState<InvestmentStrategy>("Conservative")
  const [targetAPY, setTargetAPY] = useState("20")
  const [maxDrawdown, setMaxDrawdown] = useState("15")
  const [initialMessage, setInitialMessage] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!initialMessage.trim()) {
      return
    }

    onCreate({
      strategy,
      target_apy: parseFloat(targetAPY),
      max_drawdown: parseFloat(maxDrawdown),
      initial_message: initialMessage.trim(),
    })

    // Reset form
    setStrategy("Conservative")
    setTargetAPY("20")
    setMaxDrawdown("15")
    setInitialMessage("")
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create New Chat</DialogTitle>
            <DialogDescription>
              Configure your portfolio preferences and start a conversation with
              the agent.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Portfolio Preset Settings */}
            <div className="space-y-4 rounded-lg border border-border p-4">
              <h4 className="text-sm font-semibold">Portfolio Preset</h4>

              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="strategy">Investment Strategy</Label>
                  <Select
                    value={strategy}
                    onValueChange={(value) =>
                      setStrategy(value as InvestmentStrategy)
                    }
                  >
                    <SelectTrigger id="strategy" className="rounded-lg">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Conservative">Conservative</SelectItem>
                      <SelectItem value="Balanced">Balanced</SelectItem>
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
                    max="1000"
                    step="0.1"
                    value={targetAPY}
                    onChange={(e) => setTargetAPY(e.target.value)}
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
                    onChange={(e) => setMaxDrawdown(e.target.value)}
                    className="rounded-lg"
                    required
                  />
                </div>
              </div>
            </div>

            {/* Initial Message */}
            <div className="space-y-2">
              <Label htmlFor="initial-message">Initial Message</Label>
              <Textarea
                id="initial-message"
                placeholder="예: 메이저한 코인들만 써서 구성해줘"
                value={initialMessage}
                onChange={(e) => setInitialMessage(e.target.value)}
                className="min-h-[100px] rounded-lg"
                required
              />
              <p className="text-xs text-muted-foreground">
                Describe your portfolio requirements or preferences in detail.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isCreating}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isCreating || !initialMessage.trim()}>
              {isCreating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Chat
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

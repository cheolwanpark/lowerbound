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
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Loader2 } from "lucide-react"
import type { InvestmentStrategy } from "@/lib/types"
import { PortfolioConfigInputs } from "@/components/portfolio-config-inputs"

interface NewChatModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreate: (params: {
    strategy: InvestmentStrategy
    target_apy: number
    max_drawdown: number
    initial_message: string
    title: string
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
  const [title, setTitle] = useState("")
  const [initialMessage, setInitialMessage] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!initialMessage.trim() || !title.trim()) {
      return
    }

    onCreate({
      strategy,
      target_apy: parseFloat(targetAPY),
      max_drawdown: parseFloat(maxDrawdown),
      initial_message: initialMessage.trim(),
      title: title.trim(),
    })

    // Reset form
    setStrategy("Conservative")
    setTargetAPY("20")
    setMaxDrawdown("15")
    setTitle("")
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
            {/* Chat Title */}
            <div className="space-y-2">
              <Label htmlFor="title">Chat Title</Label>
              <Input
                id="title"
                type="text"
                placeholder="e.g., Conservative Portfolio Q4 2024"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="rounded-lg"
                required
              />
              <p className="text-xs text-muted-foreground">
                Give your chat a descriptive title for easy identification.
              </p>
            </div>

            {/* Portfolio Preset Settings */}
            <div className="space-y-4 rounded-lg border border-border p-4">
              <h4 className="text-sm font-semibold">Portfolio Preset</h4>

              <PortfolioConfigInputs
                strategy={strategy}
                targetAPY={targetAPY}
                maxDrawdown={maxDrawdown}
                onStrategyChange={(value) => setStrategy(value)}
                onTargetAPYChange={setTargetAPY}
                onMaxDrawdownChange={setMaxDrawdown}
              />
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
            <Button type="submit" disabled={isCreating || !initialMessage.trim() || !title.trim()}>
              {isCreating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Chat
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronUp, Wrench, CheckCircle2, XCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ToolCall } from "@/lib/types"

interface ToolCallModalProps {
  toolCall: ToolCall | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ToolCallModal({
  toolCall,
  open,
  onOpenChange,
}: ToolCallModalProps) {
  const [showInputs, setShowInputs] = useState(false)

  if (!toolCall) return null

  const isSuccess = toolCall.status === "success"

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto scrollbar-hide">
        <DialogHeader>
          <div className="flex items-center gap-2 pr-8">
            <Wrench
              className={cn(
                "h-5 w-5",
                isSuccess ? "text-green-500" : "text-red-500",
              )}
            />
            <DialogTitle>{toolCall.tool_name}</DialogTitle>
            <Badge
              variant={isSuccess ? "default" : "destructive"}
              className="ml-auto h-6"
            >
              {isSuccess ? (
                <CheckCircle2 className="mr-1 h-3 w-3" />
              ) : (
                <XCircle className="mr-1 h-3 w-3" />
              )}
              {toolCall.status}
            </Badge>
          </div>
          <DialogDescription className="text-left">
            {new Date(toolCall.timestamp).toLocaleString("ko-KR")}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 pt-4">
          {/* Message */}
          <div>
            <h4 className="mb-2 text-sm font-semibold">Message</h4>
            <p className="rounded-lg bg-muted p-3 text-sm">
              {toolCall.message}
            </p>
          </div>

          {/* Outputs (highlighted, default open) */}
          <div>
            <h4 className="mb-2 text-sm font-semibold text-green-600 dark:text-green-400">
              Outputs
            </h4>
            <pre className="overflow-x-auto rounded-lg bg-green-50 p-3 text-xs dark:bg-green-950/30">
              {JSON.stringify(toolCall.outputs, null, 2)}
            </pre>
          </div>

          {/* Inputs (collapsible) */}
          {toolCall.inputs && Object.keys(toolCall.inputs).length > 0 && (
            <div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowInputs(!showInputs)}
                className="mb-2 h-auto p-0 text-sm font-semibold hover:bg-transparent"
              >
                Inputs
                {showInputs ? (
                  <ChevronUp className="ml-1 h-4 w-4" />
                ) : (
                  <ChevronDown className="ml-1 h-4 w-4" />
                )}
              </Button>
              {showInputs && (
                <pre className="overflow-x-auto rounded-lg bg-muted p-3 text-xs">
                  {JSON.stringify(toolCall.inputs, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

"use client"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Loader2, CheckCircle2, XCircle } from "lucide-react"
import type { ChatStatus } from "@/lib/types"

interface ChatStatusBannerProps {
  status: ChatStatus
  errorMessage?: string | null
}

export function ChatStatusBanner({
  status,
  errorMessage,
}: ChatStatusBannerProps) {
  if (status === "processing") {
    return (
      <Alert className="border-blue-500/20 bg-blue-500/5">
        <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
        <AlertTitle className="text-blue-500">Processing</AlertTitle>
        <AlertDescription className="text-blue-500/80">
          The agent is analyzing your request and building a portfolio...
        </AlertDescription>
      </Alert>
    )
  }

  if (status === "completed") {
    return (
      <Alert className="border-green-500/20 bg-green-500/5">
        <CheckCircle2 className="h-4 w-4 text-green-500" />
        <AlertTitle className="text-green-500">Completed</AlertTitle>
        <AlertDescription className="text-green-500/80">
          Portfolio analysis completed successfully
        </AlertDescription>
      </Alert>
    )
  }

  if (status === "failed") {
    return (
      <Alert variant="destructive" className="border-red-500/20 bg-red-500/5">
        <XCircle className="h-4 w-4" />
        <AlertTitle>Failed</AlertTitle>
        <AlertDescription>
          {errorMessage ||
            "An error occurred while processing your request. Please try again."}
        </AlertDescription>
      </Alert>
    )
  }

  return null
}

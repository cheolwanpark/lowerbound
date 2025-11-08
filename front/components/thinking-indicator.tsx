"use client"

import { cn } from "@/lib/utils"

interface ThinkingIndicatorProps {
  className?: string
}

export function ThinkingIndicator({ className }: ThinkingIndicatorProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-center border-t border-border bg-muted/30 py-3",
        className,
      )}
    >
      <div className="relative inline-block">
        <span
          className="animate-shimmer bg-gradient-to-r from-muted-foreground/60 via-foreground to-muted-foreground/60 bg-[length:200%_100%] bg-clip-text text-sm font-medium text-transparent"
          style={{
            animation: "shimmer 2s linear infinite",
          }}
        >
          Generating...
        </span>
      </div>
      <style jsx>{`
        @keyframes shimmer {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }
        .animate-shimmer {
          animation: shimmer 2s linear infinite;
        }
      `}</style>
    </div>
  )
}

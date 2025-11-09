"use client"

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { getTermDefinition } from "@/lib/financial-terms"

interface TermTooltipProps {
  term: string
  children: React.ReactNode
  className?: string
}

/**
 * Wrapper component that adds a hover tooltip with financial term definition
 *
 * @param term - Key from FINANCIAL_TERMS dictionary
 * @param children - The text or element to wrap (usually the term itself)
 * @param className - Optional className for the trigger element
 *
 * @example
 * <TermTooltip term="apy">APY</TermTooltip>
 * <TermTooltip term="max_drawdown">Maximum Drawdown</TermTooltip>
 */
export function TermTooltip({ term, children, className }: TermTooltipProps) {
  const definition = getTermDefinition(term)

  // If no definition found, just render children without tooltip
  if (!definition) {
    console.warn(`No definition found for term: ${term}`)
    return <>{children}</>
  }

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className={`cursor-help border-b border-dotted border-muted-foreground/50 ${className || ""}`}
          >
            {children}
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs" side="top">
          <div className="space-y-1">
            <p className="font-semibold">{definition.term}</p>
            <p className="text-sm">{definition.definition}</p>
            {definition.additionalInfo && (
              <p className="text-xs text-muted-foreground">
                {definition.additionalInfo}
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

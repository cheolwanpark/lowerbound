"use client"

import { Plus, Trash2, ChevronLeft, ChevronRight } from "lucide-react"
import type { Portfolio } from "@/types"
import { useState } from "react"

interface CollapsibleSidebarProps {
  portfolios: Portfolio[]
  activePortfolioId: string
  sidebarOpen: boolean
  onToggleSidebar: () => void
  onNewPortfolio: () => void
  onSelectPortfolio: (id: string) => void
  onDeletePortfolio: (id: string) => void
}

export default function CollapsibleSidebar({
  portfolios,
  activePortfolioId,
  sidebarOpen,
  onToggleSidebar,
  onNewPortfolio,
  onSelectPortfolio,
  onDeletePortfolio,
}: CollapsibleSidebarProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  return (
    <div
      className={`transition-all duration-300 ease-out flex flex-col bg-card border-r border-border h-screen ${
        sidebarOpen ? "w-56" : "w-16"
      }`}
    >
      {/* Header with toggle */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        {sidebarOpen && <h2 className="text-sm font-bold text-foreground">Projects</h2>}
        <button
          onClick={onToggleSidebar}
          className="p-1.5 hover:bg-muted rounded-lg transition-colors text-muted-foreground hover:text-foreground"
          aria-label="Toggle sidebar"
        >
          {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>

      {/* New Portfolio Button */}
      <div className={`p-3 border-b border-border ${sidebarOpen ? "" : "flex justify-center"}`}>
        <button
          onClick={onNewPortfolio}
          className={`flex items-center justify-center gap-2 px-3 py-2.5 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-all duration-200 shadow-sm hover:shadow-md font-medium text-sm ${
            sidebarOpen ? "w-full" : ""
          }`}
          title="New Portfolio"
        >
          <Plus className="w-4 h-4" />
          {sidebarOpen && "New"}
        </button>
      </div>

      {/* Portfolio List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {portfolios.map((portfolio) => (
          <div
            key={portfolio.id}
            className={`group rounded-lg cursor-pointer transition-all duration-150 ${
              activePortfolioId === portfolio.id
                ? "bg-primary text-primary-foreground shadow-sm"
                : "hover:bg-muted text-foreground"
            } ${sidebarOpen ? "p-3" : "p-2 flex justify-center"}`}
            onMouseEnter={() => setHoveredId(portfolio.id)}
            onMouseLeave={() => setHoveredId(null)}
            onClick={() => onSelectPortfolio(portfolio.id)}
            title={portfolio.name}
          >
            {sidebarOpen ? (
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{portfolio.name}</p>
                  <p
                    className={`text-xs mt-1 ${
                      activePortfolioId === portfolio.id ? "opacity-70" : "text-muted-foreground"
                    }`}
                  >
                    {portfolio.createdAt}
                  </p>
                </div>
                {hoveredId === portfolio.id && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeletePortfolio(portfolio.id)
                    }}
                    className="ml-2 p-1 hover:bg-destructive/20 hover:text-destructive rounded transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ) : (
              <div className="w-6 h-6 rounded bg-primary/20 flex items-center justify-center text-xs font-bold">
                {portfolio.name.charAt(0)}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer - visible only when open */}
      {sidebarOpen && (
        <div className="p-4 border-t border-border space-y-3">
          <div className="px-2 py-3 rounded-lg bg-muted/50">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">User ID</p>
            <p className="text-sm font-mono text-foreground mt-1">user_123456</p>
          </div>
        </div>
      )}
    </div>
  )
}

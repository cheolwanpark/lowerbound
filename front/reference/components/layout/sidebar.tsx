"use client"

import { Plus, Trash2, LogOut } from "lucide-react"
import type { Portfolio } from "@/types"
import { useState } from "react"

interface SidebarProps {
  portfolios: Portfolio[]
  activePortfolioId: string
  onNewPortfolio: () => void
  onSelectPortfolio: (id: string) => void
  onDeletePortfolio: (id: string) => void
}

export default function Sidebar({
  portfolios,
  activePortfolioId,
  onNewPortfolio,
  onSelectPortfolio,
  onDeletePortfolio,
}: SidebarProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  return (
    <div className="w-64 bg-card border-r border-border flex flex-col h-screen">
      {/* Logo / Header */}
      <div className="p-6 border-b border-border">
        <h1 className="text-lg font-bold text-foreground">Portfolio AI</h1>
        <p className="text-xs text-muted-foreground mt-1">Derivative Designer</p>
      </div>

      {/* New Portfolio Button */}
      <div className="p-4 border-b border-border">
        <button
          onClick={onNewPortfolio}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-all duration-200 shadow-sm hover:shadow-md font-medium text-sm"
        >
          <Plus className="w-4 h-4" />
          New Portfolio
        </button>
      </div>

      {/* Portfolio List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        {portfolios.map((portfolio) => (
          <div
            key={portfolio.id}
            className={`group p-3 rounded-lg cursor-pointer transition-all duration-150 ${
              activePortfolioId === portfolio.id
                ? "bg-primary text-primary-foreground shadow-sm"
                : "hover:bg-muted text-foreground"
            }`}
            onMouseEnter={() => setHoveredId(portfolio.id)}
            onMouseLeave={() => setHoveredId(null)}
            onClick={() => onSelectPortfolio(portfolio.id)}
          >
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
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border space-y-3">
        <div className="px-2 py-3 rounded-lg bg-muted/50">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">User ID</p>
          <p className="text-sm font-mono text-foreground mt-1">user_123456</p>
        </div>
        <button className="w-full flex items-center justify-center gap-2 px-3 py-2.5 text-sm bg-muted text-foreground hover:bg-muted/80 rounded-lg transition-colors font-medium">
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>
    </div>
  )
}

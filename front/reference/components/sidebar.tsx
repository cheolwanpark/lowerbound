"use client"

import { Plus, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

interface SidebarProps {
  activeProject: string
  onProjectChange: (projectId: string) => void
}

const mockProjects = [
  { id: "portfolio-1", name: "Conservative Strategy", version: "v3" },
  { id: "portfolio-2", name: "Aggressive Growth", version: "v5" },
  { id: "portfolio-3", name: "Balanced Portfolio", version: "v2" },
  { id: "portfolio-4", name: "DeFi Focus", version: "v4" },
]

export function Sidebar({ activeProject, onProjectChange }: SidebarProps) {
  return (
    <div className="flex w-60 flex-col border-r border-border bg-sidebar">
      {/* Logo */}
      <div className="flex items-center gap-2 border-b border-sidebar-border px-4 py-5">
        <Sparkles className="h-6 w-6 text-sidebar-primary" />
        <span className="text-lg font-semibold text-sidebar-foreground">Crypto Agent</span>
      </div>

      {/* Project List */}
      <ScrollArea className="flex-1 px-3 py-4">
        <div className="space-y-2">
          {mockProjects.map((project) => (
            <button
              key={project.id}
              onClick={() => onProjectChange(project.id)}
              className={cn(
                "w-full rounded-xl px-3 py-3 text-left transition-colors",
                activeProject === project.id
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50",
              )}
            >
              <div className="font-medium text-sm">{project.name}</div>
              <div className="text-xs text-muted-foreground mt-1">{project.version}</div>
            </button>
          ))}
        </div>
      </ScrollArea>

      {/* New Project Button */}
      <div className="border-t border-sidebar-border p-3">
        <Button
          variant="outline"
          className="w-full justify-start rounded-xl bg-transparent"
          onClick={() => {
            const newId = `portfolio-${mockProjects.length + 1}`
            onProjectChange(newId)
          }}
        >
          <Plus className="mr-2 h-4 w-4" />
          New Portfolio Session
        </Button>
      </div>
    </div>
  )
}

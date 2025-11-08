"use client"

import { useState } from "react"
import { Sidebar } from "@/components/sidebar"
import { Chat } from "@/components/chat"
import { Dashboard } from "@/components/dashboard"
import { Button } from "@/components/ui/button"

export default function Home() {
  const [activeProject, setActiveProject] = useState("portfolio-1")
  const [activeTab, setActiveTab] = useState<"chat" | "dashboard">("chat")

  return (
    <div className="dark flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar activeProject={activeProject} onProjectChange={setActiveProject} />

      {/* Main Content */}
      <div className="flex flex-1 flex-col">
        {/* Top Menu Bar */}
        <div className="flex items-center justify-between border-b border-border bg-card px-6 py-4">
          <div className="flex items-center gap-4">
            <div className="flex gap-2 rounded-xl bg-muted p-1">
              <Button
                variant={activeTab === "chat" ? "default" : "ghost"}
                size="sm"
                onClick={() => setActiveTab("chat")}
                className="rounded-lg"
              >
                Chat
              </Button>
              <Button
                variant={activeTab === "dashboard" ? "default" : "ghost"}
                size="sm"
                onClick={() => setActiveTab("dashboard")}
                className="rounded-lg"
              >
                Dashboard
              </Button>
            </div>
            <span className="text-sm text-muted-foreground">{activeProject}</span>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          {activeTab === "chat" ? <Chat projectId={activeProject} /> : <Dashboard projectId={activeProject} />}
        </div>
      </div>
    </div>
  )
}

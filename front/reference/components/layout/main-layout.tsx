"use client"

import { useState } from "react"
import CollapsibleSidebar from "./collapsible-sidebar"
import ChatHistory from "./chat-history"
import Dashboard from "./dashboard"
import type { Portfolio, Message } from "@/types"
import { mockPortfolios, mockMessages } from "@/lib/mock-data"

export default function MainLayout() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>(mockPortfolios)
  const [activePortfolioId, setActivePortfolioId] = useState<string>(portfolios[0]?.id)
  const [messages, setMessages] = useState<Message[]>(mockMessages)
  const [riskProfile, setRiskProfile] = useState<"Passive" | "Conservative" | "Aggressive">("Conservative")
  const [targetReturn, setTargetReturn] = useState<number>(10)
  const [maxDrawdown, setMaxDrawdown] = useState<number>(15)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [selectedMessageId, setSelectedMessageId] = useState<string | undefined>(undefined)
  const [settingsExpanded, setSettingsExpanded] = useState(true)

  const activePortfolio = portfolios.find((p) => p.id === activePortfolioId)

  const handleNewPortfolio = () => {
    const newPortfolio: Portfolio = {
      id: `portfolio-${Date.now()}`,
      name: `Portfolio ${portfolios.length + 1}`,
      createdAt: new Date().toLocaleDateString("ko-KR"),
    }
    const updatedPortfolios = [newPortfolio, ...portfolios]
    setPortfolios(updatedPortfolios)
    setActivePortfolioId(newPortfolio.id)
    setMessages([])
    setRiskProfile("Conservative")
    setTargetReturn(10)
    setMaxDrawdown(15)
    setSelectedMessageId(undefined)
    setSettingsExpanded(true)
  }

  const handleDeletePortfolio = (id: string) => {
    const filtered = portfolios.filter((p) => p.id !== id)
    setPortfolios(filtered)
    if (activePortfolioId === id && filtered.length > 0) {
      setActivePortfolioId(filtered[0].id)
    }
  }

  const handleSendMessage = (message: string) => {
    const newMessage: Message = {
      id: `msg-${Date.now()}`,
      type: "user",
      content: message,
      timestamp: new Date(),
    }
    setMessages([...messages, newMessage])
    setSettingsExpanded(false)

    setTimeout(() => {
      const aiMessage: Message = {
        id: `msg-${Date.now()}`,
        type: "assistant",
        content: "",
        timestamp: new Date(),
        isPortfolioResponse: true,
      }
      setMessages((prev) => [...prev, aiMessage])
      setSelectedMessageId(aiMessage.id)
    }, 500)
  }

  return (
    <div className="flex h-screen bg-background">
      <CollapsibleSidebar
        portfolios={portfolios}
        activePortfolioId={activePortfolioId}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        onNewPortfolio={handleNewPortfolio}
        onSelectPortfolio={setActivePortfolioId}
        onDeletePortfolio={handleDeletePortfolio}
      />

      <ChatHistory
        messages={messages}
        portfolioName={activePortfolio?.name}
        riskProfile={riskProfile}
        targetReturn={targetReturn}
        maxDrawdown={maxDrawdown}
        selectedMessageId={selectedMessageId}
        onSelectMessage={setSelectedMessageId}
      />

      <Dashboard
        portfolio={activePortfolio}
        messages={messages}
        onSendMessage={handleSendMessage}
        riskProfile={riskProfile}
        targetReturn={targetReturn}
        maxDrawdown={maxDrawdown}
        onRiskProfileChange={setRiskProfile}
        onTargetReturnChange={setTargetReturn}
        onMaxDrawdownChange={setMaxDrawdown}
        selectedMessageId={selectedMessageId}
        settingsExpanded={settingsExpanded}
        onSettingsExpandedChange={setSettingsExpanded}
      />
    </div>
  )
}

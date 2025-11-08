"use client"

import type React from "react"

import { useState } from "react"
import { Send, Zap, ChevronDown, ChevronUp } from "lucide-react"

interface ChatInterfaceProps {
  onSendMessage: (message: string) => void
  riskProfile: "Passive" | "Conservative" | "Aggressive"
  targetReturn: number
  maxDrawdown: number
  onRiskProfileChange: (value: "Passive" | "Conservative" | "Aggressive") => void
  onTargetReturnChange: (value: number) => void
  onMaxDrawdownChange: (value: number) => void
  showSettings: boolean
  onShowSettingsChange: (value: boolean) => void
}

export default function ChatInterface({
  onSendMessage,
  riskProfile,
  targetReturn,
  maxDrawdown,
  onRiskProfileChange,
  onTargetReturnChange,
  onMaxDrawdownChange,
  showSettings,
  onShowSettingsChange,
}: ChatInterfaceProps) {
  const [message, setMessage] = useState("")
  const [editingTargetReturn, setEditingTargetReturn] = useState(false)
  const [editingMaxDrawdown, setEditingMaxDrawdown] = useState(false)
  const [targetReturnInput, setTargetReturnInput] = useState(String(targetReturn))
  const [maxDrawdownInput, setMaxDrawdownInput] = useState(String(maxDrawdown))

  const handleSend = () => {
    if (message.trim()) {
      onSendMessage(message)
      setMessage("")
    }
  }

  const handleTargetReturnChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setTargetReturnInput(value)
    const numValue = Number(value)
    if (!isNaN(numValue) && numValue >= 0 && numValue <= 50) {
      onTargetReturnChange(numValue)
    }
  }

  const handleMaxDrawdownChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setMaxDrawdownInput(value)
    const numValue = Number(value)
    if (!isNaN(numValue) && numValue >= 5 && numValue <= 50) {
      onMaxDrawdownChange(numValue)
    }
  }

  return (
    <div className="space-y-4">
      {showSettings && (
        <div className="bg-card border border-border rounded-lg p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Zap className="w-4 h-4 text-primary" />
              Portfolio Settings
            </h3>
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide block mb-3">
                Risk Profile
              </label>
              <div className="flex gap-2">
                {["Passive", "Conservative", "Aggressive"].map((profile) => (
                  <button
                    key={profile}
                    onClick={() => onRiskProfileChange(profile as "Passive" | "Conservative" | "Aggressive")}
                    className={`px-3 py-2 text-xs font-medium rounded-md transition-all ${
                      riskProfile === profile
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "bg-muted text-muted-foreground hover:bg-muted/80"
                    }`}
                  >
                    {profile}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 pt-2">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-semibold text-muted-foreground">Target Return</label>
                  {editingTargetReturn ? (
                    <input
                      type="number"
                      min="0"
                      max="50"
                      value={targetReturnInput}
                      onChange={handleTargetReturnChange}
                      onBlur={() => {
                        setEditingTargetReturn(false)
                        setTargetReturnInput(String(targetReturn))
                      }}
                      onKeyPress={(e) => {
                        if (e.key === "Enter") {
                          setEditingTargetReturn(false)
                          setTargetReturnInput(String(targetReturn))
                        }
                      }}
                      autoFocus
                      className="w-12 px-2 py-1 text-xs bg-blue-500/10 border border-blue-500 rounded text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  ) : (
                    <button
                      onClick={() => setEditingTargetReturn(true)}
                      className="text-xs font-semibold text-blue-500 hover:opacity-80 cursor-pointer"
                    >
                      {targetReturn}%
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                  <input
                    type="range"
                    min="0"
                    max="50"
                    value={targetReturn}
                    onChange={(e) => onTargetReturnChange(Number(e.target.value))}
                    className="w-full h-1.5 rounded-full bg-muted appearance-none cursor-pointer accent-blue-500"
                  />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-semibold text-muted-foreground">Max Drawdown</label>
                  {editingMaxDrawdown ? (
                    <input
                      type="number"
                      min="5"
                      max="50"
                      value={maxDrawdownInput}
                      onChange={handleMaxDrawdownChange}
                      onBlur={() => {
                        setEditingMaxDrawdown(false)
                        setMaxDrawdownInput(String(maxDrawdown))
                      }}
                      onKeyPress={(e) => {
                        if (e.key === "Enter") {
                          setEditingMaxDrawdown(false)
                          setMaxDrawdownInput(String(maxDrawdown))
                        }
                      }}
                      autoFocus
                      className="w-12 px-2 py-1 text-xs bg-red-500/10 border border-red-500 rounded text-foreground focus:outline-none focus:ring-1 focus:ring-red-500"
                    />
                  ) : (
                    <button
                      onClick={() => setEditingMaxDrawdown(true)}
                      className="text-xs font-semibold text-red-500 hover:opacity-80 cursor-pointer"
                    >
                      {maxDrawdown}%
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />
                  <input
                    type="range"
                    min="5"
                    max="50"
                    value={maxDrawdown}
                    onChange={(e) => onMaxDrawdownChange(Number(e.target.value))}
                    className="w-full h-1.5 rounded-full bg-muted appearance-none cursor-pointer accent-red-500"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about your portfolio strategy..."
          className="flex-1 px-4 py-2.5 bg-card border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all shadow-sm"
        />
        <button
          onClick={() => onShowSettingsChange(!showSettings)}
          className={`px-4 py-2.5 rounded-lg transition-all duration-200 flex items-center gap-2 font-medium shadow-sm ${
            showSettings
              ? "bg-primary text-primary-foreground hover:opacity-90"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
        >
          {showSettings ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        <button
          onClick={handleSend}
          className="px-4 py-2.5 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-all duration-200 flex items-center gap-2 font-medium shadow-sm hover:shadow-md"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

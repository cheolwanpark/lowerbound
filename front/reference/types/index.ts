export interface Portfolio {
  id: string
  name: string
  createdAt: string
}

export interface Message {
  id: string
  type: "user" | "assistant"
  content: string
  timestamp: Date
  isPortfolioResponse?: boolean
}

export interface ChatHistoryProps {
  messages: Message[]
  portfolioName?: string
  riskProfile: string
  targetReturn: number
  maxDrawdown: number
  selectedMessageId?: string
  onSelectMessage?: (messageId: string) => void
}

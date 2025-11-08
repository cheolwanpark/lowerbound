// Type definitions for the crypto portfolio agent API
// Based on agent/API.md

// ============================================================================
// Chat List Types
// ============================================================================

export type ChatStatus = "queued" | "processing" | "completed" | "failed" | "timeout"
export type InvestmentStrategy = "Passive" | "Conservative" | "Aggressive"

export interface ChatListItem {
  id: string
  status: ChatStatus
  strategy: InvestmentStrategy
  target_apy: number
  max_drawdown: number
  title?: string
  has_portfolio: boolean
  message_count: number
  created_at: string
  updated_at: string
}

// ============================================================================
// Message Types
// ============================================================================

export interface Reasoning {
  summary: string
  detail: string
  timestamp: string
}

export interface ToolCall {
  tool_name: string
  message: string
  timestamp: string
  inputs: Record<string, any>
  outputs: Record<string, any>
  status: "success" | "error"
}

export type MessageType = "user" | "agent" | "system"

export interface BaseMessage {
  type: MessageType
  message: string
  timestamp: string
  reasonings: Reasoning[]
  toolcalls: ToolCall[]
}

// ============================================================================
// Portfolio Types
// ============================================================================

export type PositionType = "spot" | "futures" | "lending_supply" | "lending_borrow"
export type BorrowType = "variable" | "stable" | null

export interface Position {
  asset: string
  quantity: number
  position_type: PositionType
  entry_price: number
  leverage: number
  entry_timestamp: string | null
  entry_index: number | null
  borrow_type: BorrowType
}

export interface PortfolioVersion {
  version: number
  positions: Position[]
  explanation: string
  timestamp: string
}

// ============================================================================
// Chat Detail Types
// ============================================================================

export interface ChatDetail {
  id: string
  status: ChatStatus
  strategy: InvestmentStrategy
  target_apy: number
  max_drawdown: number
  title?: string
  messages: BaseMessage[]
  portfolio: Position[] | null
  portfolio_versions: PortfolioVersion[]
  error_message: string | null
  created_at: string
  updated_at: string
}

// ============================================================================
// Portfolio Response Type
// ============================================================================

export interface PortfolioResponse {
  chat_id: string
  portfolio_versions: PortfolioVersion[]
  latest_portfolio: Position[]
  has_portfolio: boolean
}

// ============================================================================
// Create Chat Types
// ============================================================================

export interface CreateChatParams {
  strategy: InvestmentStrategy
  target_apy: number
  max_drawdown: number
  initial_message: string
  title: string
}

// ============================================================================
// UI State Types
// ============================================================================

export interface ChatState {
  selectedChatId: string | null
  isNewChatModalOpen: boolean
}

export interface LoadingState {
  isLoading: boolean
  error: Error | null
}

// ============================================================================
// Validation Helpers
// ============================================================================

/**
 * Clamp APY value to valid range (0-200%)
 */
export function clampAPY(value: number): number {
  return Math.max(0, Math.min(200, value))
}

/**
 * Clamp max drawdown value to valid range (0-100%)
 */
export function clampDrawdown(value: number): number {
  return Math.max(0, Math.min(100, value))
}

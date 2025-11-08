// API client for communicating with the crypto portfolio agent backend
import type {
  ChatListItem,
  ChatDetail,
  PortfolioResponse,
  CreateChatParams,
} from "./types"

// Get API URL from environment variable, default to localhost:8001
const getApiUrl = () => {
  if (typeof window === "undefined") {
    // Server-side: use environment variable or default
    return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
  }
  // Client-side: use environment variable or default
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
}

// ============================================================================
// Error Handling
// ============================================================================

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text()
    throw new ApiError(
      response.status,
      response.statusText,
      errorText || `Request failed with status ${response.status}`,
    )
  }

  try {
    return await response.json()
  } catch (error) {
    throw new Error("Failed to parse JSON response")
  }
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch all chat sessions
 * GET /chat
 */
export async function fetchChats(): Promise<ChatListItem[]> {
  const apiUrl = getApiUrl()
  const response = await fetch(`${apiUrl}/chat`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })

  return handleResponse<ChatListItem[]>(response)
}

/**
 * Fetch detailed information about a specific chat session
 * GET /chat/{id}
 */
export async function fetchChatDetail(id: string): Promise<ChatDetail> {
  const apiUrl = getApiUrl()
  const response = await fetch(`${apiUrl}/chat/${id}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })

  return handleResponse<ChatDetail>(response)
}

/**
 * Fetch portfolio information for a specific chat session
 * GET /chat/{id}/portfolio
 */
export async function fetchChatPortfolio(
  id: string,
): Promise<PortfolioResponse> {
  const apiUrl = getApiUrl()
  const response = await fetch(`${apiUrl}/chat/${id}/portfolio`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })

  return handleResponse<PortfolioResponse>(response)
}

/**
 * Create a new chat session
 * POST /chat
 */
export async function createChat(
  params: CreateChatParams,
): Promise<ChatDetail> {
  const apiUrl = getApiUrl()
  const response = await fetch(`${apiUrl}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_prompt: params.initial_message,
      strategy: params.strategy,
      target_apy: params.target_apy,
      max_drawdown: params.max_drawdown,
      title: params.title,
    }),
  })

  return handleResponse<ChatDetail>(response)
}

/**
 * Send a followup message to an existing chat session
 * POST /chat/{id}/followup
 */
export async function sendFollowup(
  chatId: string,
  prompt: string,
  config?: {
    strategy?: "Passive" | "Conservative" | "Aggressive"
    target_apy?: number
    max_drawdown?: number
  },
): Promise<ChatDetail> {
  const apiUrl = getApiUrl()
  const body: Record<string, unknown> = { prompt }

  // Add optional configuration parameters if provided
  if (config?.strategy) body.strategy = config.strategy
  if (config?.target_apy !== undefined) body.target_apy = config.target_apy
  if (config?.max_drawdown !== undefined) body.max_drawdown = config.max_drawdown

  const response = await fetch(`${apiUrl}/chat/${chatId}/followup`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  })

  return handleResponse<ChatDetail>(response)
}

/**
 * @deprecated Use sendFollowup instead
 * Legacy function for backward compatibility
 */
export async function sendMessage(
  chatId: string,
  message: string,
): Promise<ChatDetail> {
  return sendFollowup(chatId, message)
}

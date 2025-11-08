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
    }),
  })

  return handleResponse<ChatDetail>(response)
}

/**
 * Send a message to an existing chat session
 * POST /chat/{id}/message
 */
export async function sendMessage(
  chatId: string,
  message: string,
): Promise<ChatDetail> {
  const apiUrl = getApiUrl()
  const response = await fetch(`${apiUrl}/chat/${chatId}/message`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
    }),
  })

  return handleResponse<ChatDetail>(response)
}

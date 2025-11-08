"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { fetchChatDetail } from "@/lib/api-client"
import type { ChatDetail } from "@/lib/types"

const POLLING_INTERVAL = 3000 // 3 seconds

export interface UseChatDetailReturn {
  chat: ChatDetail | null
  isLoading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

/**
 * Hook to fetch and poll chat detail
 * Polls every 3 seconds while status is "processing"
 * Stops polling when status is "completed" or "failed"
 */
export function useChatDetail(chatId: string | null): UseChatDetailReturn {
  const [chat, setChat] = useState<ChatDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const fetchChat = useCallback(async () => {
    if (!chatId) {
      setChat(null)
      setIsLoading(false)
      return
    }

    try {
      const data = await fetchChatDetail(chatId)
      setChat(data)
      setError(null)

      // Stop polling if chat is completed or failed
      if (
        data.status === "completed" ||
        data.status === "failed"
      ) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
      }
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error("Failed to fetch chat detail"),
      )
    } finally {
      setIsLoading(false)
    }
  }, [chatId])

  // Initial fetch
  useEffect(() => {
    if (chatId) {
      setIsLoading(true)
      fetchChat()
    } else {
      setChat(null)
      setIsLoading(false)
    }
  }, [chatId, fetchChat])

  // Set up polling for processing chats
  useEffect(() => {
    if (!chatId) return

    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }

    // Only poll if chat is processing or not yet loaded
    if (!chat || chat.status === "processing") {
      intervalRef.current = setInterval(() => {
        fetchChat()
      }, POLLING_INTERVAL)
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [chatId, chat?.status, fetchChat])

  return {
    chat,
    isLoading,
    error,
    refetch: fetchChat,
  }
}

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
  const chatIdRef = useRef<string | null>(null)
  const previousStatusRef = useRef<string | null>(null)

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
      // Set error but don't stop polling - continue trying
      setError(
        err instanceof Error ? err : new Error("Failed to fetch chat detail"),
      )
      // Don't clear the interval on error - let polling continue
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
    if (!chatId) {
      // Clear interval when chatId is null
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    // If chatId changed, clear existing interval and reset
    if (chatIdRef.current !== chatId) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      chatIdRef.current = chatId
      previousStatusRef.current = null
    }

    // Restart polling if status changed from completed/failed to queued/processing
    const currentStatus = chat?.status
    const previousStatus = previousStatusRef.current

    if (currentStatus && previousStatus) {
      const wasInactive = previousStatus === "completed" || previousStatus === "failed"
      const isNowActive = currentStatus === "queued" || currentStatus === "processing"

      if (wasInactive && isNowActive && !intervalRef.current) {
        // Restart polling when chat becomes active again
        intervalRef.current = setInterval(() => {
          fetchChat()
        }, POLLING_INTERVAL)
      }
    }

    // Update previous status
    if (currentStatus) {
      previousStatusRef.current = currentStatus
    }

    // Start polling immediately for new or processing chats
    // The fetchChat function will automatically stop polling when status becomes completed/failed
    if (!intervalRef.current) {
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
  }, [chatId, fetchChat, chat?.status])

  return {
    chat,
    isLoading,
    error,
    refetch: fetchChat,
  }
}

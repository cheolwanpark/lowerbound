"use client"

import { useState, useCallback } from "react"
import { createChat } from "@/lib/api-client"
import type { CreateChatParams, ChatDetail } from "@/lib/types"

export interface UseCreateChatReturn {
  create: (params: CreateChatParams) => Promise<ChatDetail | null>
  isCreating: boolean
  error: Error | null
}

/**
 * Hook to create a new chat session
 */
export function useCreateChat(): UseCreateChatReturn {
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const create = useCallback(async (params: CreateChatParams) => {
    setIsCreating(true)
    setError(null)

    try {
      const chat = await createChat(params)
      return chat
    } catch (err) {
      const error =
        err instanceof Error ? err : new Error("Failed to create chat")
      setError(error)
      return null
    } finally {
      setIsCreating(false)
    }
  }, [])

  return {
    create,
    isCreating,
    error,
  }
}

import { StreamChunk } from '@/types'

/**
 * Handles streaming responses from the chat API
 * Parses NDJSON (newline-delimited JSON) chunks
 */
export async function handleStreamingResponse(
  response: Response,
  onChunk: (chunk: StreamChunk) => void,
  onComplete: () => void,
  onError: (error: string) => void
) {
  if (!response.ok) {
    onError(`API error: ${response.statusText}`)
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    onError('No response body')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()

      if (done) {
        // Process any remaining data in buffer
        if (buffer.trim()) {
          try {
            const chunk = JSON.parse(buffer) as StreamChunk
            onChunk(chunk)
          } catch (e) {
            console.error('Failed to parse final chunk:', e)
          }
        }
        onComplete()
        break
      }

      // Decode the chunk and add to buffer
      buffer += decoder.decode(value, { stream: true })

      // Process complete lines (NDJSON format)
      const lines = buffer.split('\n')
      // Keep the last incomplete line in buffer
      buffer = lines.pop() || ''

      // Parse each complete line as JSON
      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed) continue

        try {
          const chunk = JSON.parse(trimmed) as StreamChunk
          onChunk(chunk)
        } catch (e) {
          console.error('Failed to parse chunk:', trimmed, e)
          // Continue processing other chunks even if one fails
        }
      }
    }
  } catch (error) {
    onError(`Stream error: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

/**
 * Sends a message to the chat API and handles the streaming response
 */
export async function sendChatMessage(
  message: string,
  onChunk: (chunk: StreamChunk) => void,
  onComplete: () => void,
  onError: (error: string) => void
) {
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    })

    await handleStreamingResponse(response, onChunk, onComplete, onError)
  } catch (error) {
    onError(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

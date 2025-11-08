'use client'

import { useReducer } from 'react'
import { chatReducer, initialChatState } from '@/lib/chat-reducer'
import { sendChatMessage } from '@/lib/stream-handler'
import { MessageList } from './message-list'
import { ChatInput } from './chat-input'
import { Card } from '@/components/ui/card'
import { Loader2 } from 'lucide-react'

export function ChatContainer() {
  const [state, dispatch] = useReducer(chatReducer, initialChatState)

  const handleSendMessage = async (message: string) => {
    // Add user message
    dispatch({ type: 'ADD_USER_MESSAGE', payload: { content: message } })

    // Start streaming assistant response
    const messageId = crypto.randomUUID()
    dispatch({ type: 'START_ASSISTANT_MESSAGE', payload: { messageId } })

    // Send request and handle streaming response
    await sendChatMessage(
      message,
      // On each chunk
      (chunk) => {
        dispatch({ type: 'APPEND_CHUNK', payload: { messageId, chunk } })
      },
      // On complete
      () => {
        dispatch({ type: 'FINISH_STREAMING', payload: { messageId } })
      },
      // On error
      (error) => {
        dispatch({ type: 'SET_ERROR', payload: { error } })
      }
    )
  }

  return (
    <div className="flex h-screen w-full items-center justify-center bg-background p-4">
      <Card className="flex h-full max-h-[900px] w-full max-w-4xl flex-col overflow-hidden">
        <div className="border-b px-6 py-4">
          <h1 className="text-xl font-semibold">Crypto Portfolio Chat</h1>
          <p className="text-sm text-muted-foreground">
            Ask questions about your crypto portfolio
          </p>
        </div>

        {state.error && (
          <div className="mx-4 mt-4 rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {state.error}
          </div>
        )}

        {state.isLoading && state.messages.length === 0 && (
          <div className="flex items-center gap-2 px-6 py-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Thinking...
          </div>
        )}

        <MessageList messages={state.messages} />
        <ChatInput onSend={handleSendMessage} disabled={state.isLoading} />
      </Card>
    </div>
  )
}

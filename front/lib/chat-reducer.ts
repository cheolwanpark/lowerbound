import { ChatState, ChatAction } from '@/types'

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'ADD_USER_MESSAGE': {
      const newMessage = {
        id: crypto.randomUUID(),
        role: 'user' as const,
        chunks: [{ type: 'text' as const, content: action.payload.content }],
        timestamp: new Date(),
      }
      return {
        ...state,
        messages: [...state.messages, newMessage],
      }
    }

    case 'START_ASSISTANT_MESSAGE': {
      const newMessage = {
        id: action.payload.messageId,
        role: 'assistant' as const,
        chunks: [],
        timestamp: new Date(),
        isStreaming: true,
      }
      return {
        ...state,
        messages: [...state.messages, newMessage],
        isLoading: true,
        streamingMessageId: action.payload.messageId,
      }
    }

    case 'APPEND_CHUNK': {
      return {
        ...state,
        messages: state.messages.map((msg) =>
          msg.id === action.payload.messageId
            ? { ...msg, chunks: [...msg.chunks, action.payload.chunk] }
            : msg
        ),
      }
    }

    case 'FINISH_STREAMING': {
      return {
        ...state,
        messages: state.messages.map((msg) =>
          msg.id === action.payload.messageId
            ? { ...msg, isStreaming: false }
            : msg
        ),
        isLoading: false,
        streamingMessageId: null,
      }
    }

    case 'SET_ERROR': {
      return {
        ...state,
        error: action.payload.error,
        isLoading: false,
        streamingMessageId: null,
      }
    }

    case 'CLEAR_ERROR': {
      return {
        ...state,
        error: null,
      }
    }

    default:
      return state
  }
}

export const initialChatState: ChatState = {
  messages: [],
  isLoading: false,
  error: null,
  streamingMessageId: null,
}

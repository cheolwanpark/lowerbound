// Streaming chunk types - NDJSON protocol
export type TextChunk = {
  type: 'text'
  content: string
}

export type GraphChunk = {
  type: 'graph'
  data: {
    labels: string[]
    values: number[]
  }
}

export type TableChunk = {
  type: 'table'
  data: {
    headers: string[]
    rows: string[][]
  }
}

export type StreamChunk = TextChunk | GraphChunk | TableChunk

// Message structure
export type Message = {
  id: string
  role: 'user' | 'assistant'
  chunks: StreamChunk[]
  timestamp: Date
  isStreaming?: boolean
}

// Chat state
export type ChatState = {
  messages: Message[]
  isLoading: boolean
  error: string | null
  streamingMessageId: string | null
}

// Chat actions for reducer
export type ChatAction =
  | { type: 'ADD_USER_MESSAGE'; payload: { content: string } }
  | { type: 'START_ASSISTANT_MESSAGE'; payload: { messageId: string } }
  | { type: 'APPEND_CHUNK'; payload: { messageId: string; chunk: StreamChunk } }
  | { type: 'FINISH_STREAMING'; payload: { messageId: string } }
  | { type: 'SET_ERROR'; payload: { error: string } }
  | { type: 'CLEAR_ERROR' }

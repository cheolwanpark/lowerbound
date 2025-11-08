'use client'

import { Message } from '@/types'
import { cn } from '@/lib/utils'
import { GraphRenderer } from './graph-renderer'
import { TableRenderer } from './table-renderer'

interface MessageItemProps {
  message: Message
}

export function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === 'user'

  return (
    <div
      className={cn(
        'flex w-full',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-3',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
        )}
      >
        {message.chunks.map((chunk, index) => (
          <div key={index}>
            {chunk.type === 'text' && (
              <div className="whitespace-pre-wrap text-sm">
                {chunk.content}
              </div>
            )}
            {chunk.type === 'graph' && !isUser && (
              <GraphRenderer data={chunk.data} />
            )}
            {chunk.type === 'table' && !isUser && (
              <TableRenderer data={chunk.data} />
            )}
          </div>
        ))}
        {message.isStreaming && (
          <span className="inline-block h-4 w-1 animate-pulse bg-foreground/50 ml-1" />
        )}
      </div>
    </div>
  )
}

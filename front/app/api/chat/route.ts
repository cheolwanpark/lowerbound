import { NextRequest } from 'next/server'
import { generateMockGraphData, generateMockTableData, generateMockTextChunks } from '@/lib/mock-data'
import { StreamChunk } from '@/types'

export const runtime = 'edge'

// Helper to create a delay
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

// Helper to encode chunk to NDJSON format
function encodeChunk(chunk: StreamChunk): string {
  return JSON.stringify(chunk) + '\n'
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    if (!body?.message || typeof body.message !== 'string') {
      return new Response('Invalid request: message is required', { status: 400 })
    }
  } catch {
    return new Response('Invalid JSON', { status: 400 })
  }

  // Create a readable stream
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {
      try {
        const textChunks = generateMockTextChunks()
        const graphData = generateMockGraphData()
        const tableData = generateMockTableData()

        // Build complete sequence: text → graph → text → table → text
        const sequence: StreamChunk[] = [
          ...textChunks.slice(0, 6).map(content => ({ type: 'text' as const, content })),
          { type: 'graph' as const, data: graphData },
          { type: 'text' as const, content: textChunks[6] },
          { type: 'table' as const, data: tableData },
          ...textChunks.slice(7).map(content => ({ type: 'text' as const, content })),
        ]

        // Stream all chunks with delays
        for (const chunk of sequence) {
          controller.enqueue(encoder.encode(encodeChunk(chunk)))
          await delay(100)
        }

        controller.close()
      } catch (error) {
        controller.error(error)
      }
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'application/x-ndjson',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  })
}

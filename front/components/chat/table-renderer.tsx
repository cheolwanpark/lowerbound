'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TableChunk } from '@/types'
import { cn } from '@/lib/utils'

interface TableRendererProps {
  data: TableChunk['data']
}

export const TableRenderer = React.memo(function TableRenderer({ data }: TableRendererProps) {
  return (
    <Card className="my-4">
      <CardHeader>
        <CardTitle className="text-base">Portfolio Holdings</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                {data.headers.map((header, index) => (
                  <th
                    key={index}
                    className={cn(
                      "px-4 py-3 text-left text-sm font-medium",
                      index === 0 && "pl-6"
                    )}
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="border-b last:border-0">
                  {row.map((cell, cellIndex) => (
                    <td
                      key={cellIndex}
                      className={cn(
                        "px-4 py-3 text-sm",
                        cellIndex === 0 && "pl-6 font-medium"
                      )}
                    >
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
})

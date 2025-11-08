"use client"

import { useState } from "react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartPie } from "@/components/chart-pie"
import { ChartBar } from "@/components/chart-bar"
import { ChartLine } from "@/components/chart-line"

interface DashboardProps {
  projectId: string
}

export function Dashboard({ projectId }: DashboardProps) {
  const [selectedVersion, setSelectedVersion] = useState("v3")

  return (
    <div className="h-full overflow-auto bg-background p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Portfolio Analytics</h1>
          <Select value={selectedVersion} onValueChange={setSelectedVersion}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="v1">Version 1</SelectItem>
              <SelectItem value="v2">Version 2</SelectItem>
              <SelectItem value="v3">Version 3</SelectItem>
              <SelectItem value="v4">Version 4</SelectItem>
              <SelectItem value="v5">Version 5</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Charts Grid */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Pie Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Asset Allocation</CardTitle>
              <CardDescription>Current portfolio distribution</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartPie />
            </CardContent>
          </Card>

          {/* Bar Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Risk vs Expected Return</CardTitle>
              <CardDescription>Comparison by asset</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartBar />
            </CardContent>
          </Card>

          {/* Line Chart - Full Width */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Historical Performance</CardTitle>
              <CardDescription>Portfolio value and drawdown over time</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartLine />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

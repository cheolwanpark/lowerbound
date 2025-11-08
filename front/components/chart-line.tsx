"use client"

import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from "@/components/ui/chart"

const data = [
  { month: "Jan", value: 100, drawdown: 0 },
  { month: "Feb", value: 105, drawdown: -2 },
  { month: "Mar", value: 112, drawdown: -5 },
  { month: "Apr", value: 108, drawdown: -8 },
  { month: "May", value: 118, drawdown: -3 },
  { month: "Jun", value: 125, drawdown: -1 },
  { month: "Jul", value: 122, drawdown: -6 },
  { month: "Aug", value: 130, drawdown: -4 },
  { month: "Sep", value: 138, drawdown: -2 },
  { month: "Oct", value: 145, drawdown: -1 },
  { month: "Nov", value: 152, drawdown: 0 },
  { month: "Dec", value: 160, drawdown: 0 },
]

const chartConfig = {
  value: {
    label: "Portfolio Value",
    color: "hsl(var(--chart-1))",
  },
  drawdown: {
    label: "Drawdown %",
    color: "hsl(var(--chart-2))",
  },
}

export function ChartLine() {
  return (
    <ChartContainer config={chartConfig} className="h-[300px] w-full">
      <LineChart data={data}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="month" tickLine={false} axisLine={false} tickMargin={8} />
        <YAxis tickLine={false} axisLine={false} tickMargin={8} />
        <ChartTooltip content={<ChartTooltipContent />} />
        <ChartLegend content={<ChartLegendContent />} />
        <Line type="monotone" dataKey="value" stroke="var(--color-value)" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="drawdown" stroke="var(--color-drawdown)" strokeWidth={2} dot={false} />
      </LineChart>
    </ChartContainer>
  )
}

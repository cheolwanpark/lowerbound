"use client"

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from "@/components/ui/chart"

const data = [
  { asset: "BTC", risk: 65, return: 85 },
  { asset: "ETH", risk: 70, return: 90 },
  { asset: "SOL", risk: 80, return: 110 },
  { asset: "USDC", risk: 5, return: 8 },
]

const chartConfig = {
  risk: {
    label: "Risk Score",
    color: "hsl(var(--chart-1))",
  },
  return: {
    label: "Expected Return",
    color: "hsl(var(--chart-2))",
  },
}

export function ChartBar() {
  return (
    <ChartContainer config={chartConfig} className="h-[300px] w-full">
      <BarChart data={data}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="asset" tickLine={false} tickMargin={10} axisLine={false} />
        <YAxis tickLine={false} axisLine={false} tickMargin={10} />
        <ChartTooltip content={<ChartTooltipContent />} />
        <ChartLegend content={<ChartLegendContent />} />
        <Bar dataKey="risk" fill="var(--color-risk)" radius={[8, 8, 0, 0]} />
        <Bar dataKey="return" fill="var(--color-return)" radius={[8, 8, 0, 0]} />
      </BarChart>
    </ChartContainer>
  )
}

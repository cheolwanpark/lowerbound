"use client"

import { Label, Pie, PieChart } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"

const data = [
  { asset: "BTC", value: 40, fill: "hsl(var(--chart-1))" },
  { asset: "ETH", value: 35, fill: "hsl(var(--chart-2))" },
  { asset: "SOL", value: 15, fill: "hsl(var(--chart-3))" },
  { asset: "USDC", value: 10, fill: "hsl(var(--chart-4))" },
]

const chartConfig = {
  value: {
    label: "Allocation",
  },
  BTC: {
    label: "Bitcoin",
    color: "hsl(var(--chart-1))",
  },
  ETH: {
    label: "Ethereum",
    color: "hsl(var(--chart-2))",
  },
  SOL: {
    label: "Solana",
    color: "hsl(var(--chart-3))",
  },
  USDC: {
    label: "USD Coin",
    color: "hsl(var(--chart-4))",
  },
}

export function ChartPie() {
  const totalValue = data.reduce((acc, curr) => acc + curr.value, 0)

  return (
    <ChartContainer config={chartConfig} className="mx-auto aspect-square max-h-[300px]">
      <PieChart>
        <ChartTooltip cursor={false} content={<ChartTooltipContent hideLabel />} />
        <Pie data={data} dataKey="value" nameKey="asset" innerRadius={60} strokeWidth={5}>
          <Label
            content={({ viewBox }) => {
              if (viewBox && "cx" in viewBox && "cy" in viewBox) {
                return (
                  <text x={viewBox.cx} y={viewBox.cy} textAnchor="middle" dominantBaseline="middle">
                    <tspan x={viewBox.cx} y={viewBox.cy} className="fill-foreground text-3xl font-bold">
                      {totalValue}%
                    </tspan>
                    <tspan x={viewBox.cx} y={(viewBox.cy || 0) + 24} className="fill-muted-foreground">
                      Total
                    </tspan>
                  </text>
                )
              }
            }}
          />
        </Pie>
      </PieChart>
    </ChartContainer>
  )
}

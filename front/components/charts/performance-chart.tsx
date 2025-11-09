"use client"

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from "recharts"
import type { PerformanceGraphData } from "@/lib/types"

export function PerformanceChart({ data }: { data: PerformanceGraphData }) {
  // Format data for chart - X is price change %, Y is return %
  const chartData = data.data_points.map((point) => ({
    x: point.x,  // Price change %
    Portfolio: point.portfolio_return_pct,
    BTC: point.btc_return_pct,
    USDT: point.usdt_return_pct,
  }))

  return (
    <div className="rounded-xl border bg-card p-6">
      <h3 className="text-lg font-semibold mb-4">
        Portfolio Performance vs Baselines
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="x"
            label={{
              value: "Price Change (%)",
              position: "insideBottom",
              offset: -5,
            }}
            tickFormatter={(value) => `${value.toFixed(0)}%`}
          />
          <YAxis
            label={{
              value: "Return (%)",
              angle: -90,
              position: "insideLeft",
            }}
            tickFormatter={(value) => `${value.toFixed(0)}%`}
          />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(2)}%`, ""]}
            labelFormatter={(label) => `${label}% price change`}
          />
          <Legend verticalAlign="bottom" wrapperStyle={{ paddingTop: "20px" }} />
          <ReferenceLine
            y={0}
            stroke="#666"
            strokeWidth={2}
            strokeDasharray="5 5"
            label={{ value: "Break Even", position: "right" }}
          />
          <ReferenceLine
            x={0}
            stroke="#10b981"
            strokeDasharray="3 3"
            label="Current"
          />
          <Line
            type="monotone"
            dataKey="Portfolio"
            stroke="#8884d8"
            strokeWidth={2}
            dot={false}
            name="Portfolio"
          />
          <Line
            type="monotone"
            dataKey="BTC"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            name="BTC Baseline"
          />
          <Line
            type="monotone"
            dataKey="USDT"
            stroke="#10b981"
            strokeWidth={1}
            strokeDasharray="5 5"
            dot={false}
            name="USDT Interest (Annual)"
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-4 flex justify-between text-sm text-muted-foreground">
        <span>Min Return: {data.return_range.min.toFixed(2)}%</span>
        <span>Current: {data.return_range.current.toFixed(2)}%</span>
        <span>Max Return: {data.return_range.max.toFixed(2)}%</span>
      </div>
    </div>
  )
}

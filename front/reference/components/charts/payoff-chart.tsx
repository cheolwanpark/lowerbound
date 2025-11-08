"use client"

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

const generateChartData = (riskProfile: string) => {
  const baseData = []
  for (let i = -50; i <= 50; i += 5) {
    baseData.push({ price: i })
  }

  return baseData.map((item) => {
    let pnl = 0
    if (riskProfile === "Passive") {
      pnl = item.price - Math.max(0, -item.price - 5)
    } else if (riskProfile === "Conservative") {
      pnl = item.price - Math.max(0, -item.price - 8) - Math.max(0, item.price - 15) * 0.3
    } else {
      pnl = item.price + Math.max(0, item.price - 10) - Math.max(0, -item.price - 5)
    }
    return { ...item, pnl }
  })
}

interface PayoffChartProps {
  riskProfile: "Passive" | "Conservative" | "Aggressive"
}

export default function PayoffChart({ riskProfile }: PayoffChartProps) {
  const data = generateChartData(riskProfile)

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="price"
          label={{ value: "Underlying Price Change (%)", position: "insideBottomRight", offset: -5 }}
        />
        <YAxis label={{ value: "P&L (%)", angle: -90, position: "insideLeft" }} />
        <Tooltip formatter={(value) => `${value.toFixed(2)}%`} />
        <Line type="monotone" dataKey="pnl" stroke="#8b5cf6" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

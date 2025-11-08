"use client"

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"

const generateSimulationData = (riskProfile: string) => {
  const data = []
  const days = 90
  const volatility = riskProfile === "Aggressive" ? 0.03 : riskProfile === "Conservative" ? 0.015 : 0.01

  let portfolio = 100
  let btc = 100
  let eth = 100

  for (let i = 0; i <= days; i += 7) {
    const randomReturn = (Math.random() - 0.5) * volatility * 2
    const dailyReturn = randomReturn / (7 * 100)

    if (riskProfile === "Passive") {
      portfolio = portfolio * (1 + dailyReturn * 0.7 - 0.0002)
    } else if (riskProfile === "Conservative") {
      portfolio = portfolio * (1 + dailyReturn * 0.9 - 0.0003)
    } else {
      portfolio = portfolio * (1 + dailyReturn * 1.2 - 0.0004)
    }

    btc = btc * (1 + randomReturn * 0.6)
    eth = eth * (1 + randomReturn * 0.4)

    data.push({
      week: i,
      portfolio: Number.parseFloat(portfolio.toFixed(2)),
      btc: Number.parseFloat(btc.toFixed(2)),
      eth: Number.parseFloat(eth.toFixed(2)),
    })
  }

  return data
}

interface PerformanceSimulationProps {
  riskProfile: "Passive" | "Conservative" | "Aggressive"
}

export default function PerformanceSimulation({ riskProfile }: PerformanceSimulationProps) {
  const data = generateSimulationData(riskProfile)

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="week" label={{ value: "Days", position: "insideBottomRight", offset: -5 }} stroke="#9ca3af" />
        <YAxis label={{ value: "Portfolio Value ($)", angle: -90, position: "insideLeft" }} stroke="#9ca3af" />
        <Tooltip
          formatter={(value) => `$${value.toFixed(2)}`}
          contentStyle={{
            backgroundColor: "#1f2937",
            border: "1px solid #374151",
            borderRadius: "6px",
          }}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="portfolio"
          stroke="#3b82f6"
          strokeWidth={2.5}
          dot={false}
          name="Portfolio"
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="btc"
          stroke="#f59e0b"
          strokeWidth={1.5}
          dot={false}
          name="BTC"
          strokeDasharray="5 5"
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="eth"
          stroke="#10b981"
          strokeWidth={1.5}
          dot={false}
          name="ETH"
          strokeDasharray="5 5"
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

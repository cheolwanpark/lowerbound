"use client"

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

const generateStressData = (riskProfile: string, targetReturn: number) => {
  const baseReturns = {
    Passive: targetReturn * 0.6,
    Conservative: targetReturn * 0.8,
    Aggressive: targetReturn,
  }

  return [
    { scenario: "Normal", return: baseReturns[riskProfile as keyof typeof baseReturns] },
    { scenario: "-10%", return: baseReturns[riskProfile as keyof typeof baseReturns] * 0.7 },
    { scenario: "-30%", return: baseReturns[riskProfile as keyof typeof baseReturns] * 0.3 },
    { scenario: "-50%", return: baseReturns[riskProfile as keyof typeof baseReturns] * -0.5 },
  ]
}

interface StressAnalysisProps {
  riskProfile: "Passive" | "Conservative" | "Aggressive"
  targetReturn: number
}

export default function StressAnalysis({ riskProfile, targetReturn }: StressAnalysisProps) {
  const data = generateStressData(riskProfile, targetReturn)

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="scenario" />
        <YAxis label={{ value: "Return (%)", angle: -90, position: "insideLeft" }} />
        <Tooltip formatter={(value) => `${value.toFixed(2)}%`} />
        <Bar dataKey="return" fill="#8b5cf6" />
      </BarChart>
    </ResponsiveContainer>
  )
}

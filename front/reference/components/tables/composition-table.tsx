"use client"

const getCompositionData = (riskProfile: string) => {
  const data = {
    Passive: [
      { asset: "BTC Spot", allocation: "60%", return: "5-8%", risk: "Low" },
      { asset: "ETH Spot", allocation: "25%", return: "5-8%", risk: "Low" },
      { asset: "BTC Put Option", allocation: "10%", return: "0-2%", risk: "Low" },
      { asset: "Stablecoin", allocation: "5%", return: "4%", risk: "Minimal" },
    ],
    Conservative: [
      { asset: "BTC Spot", allocation: "40%", return: "8-12%", risk: "Medium" },
      { asset: "ETH Spot", allocation: "30%", return: "8-12%", risk: "Medium" },
      { asset: "Call Spread", allocation: "15%", return: "10-15%", risk: "Medium" },
      { asset: "Stablecoin", allocation: "15%", return: "4%", risk: "Minimal" },
    ],
    Aggressive: [
      { asset: "BTC Call Option", allocation: "40%", return: "20-50%", risk: "High" },
      { asset: "ETH Call Spread", allocation: "35%", return: "15-40%", risk: "High" },
      { asset: "BTC Spot", allocation: "15%", return: "10-20%", risk: "High" },
      { asset: "Leverage Staking", allocation: "10%", return: "25-35%", risk: "Very High" },
    ],
  }
  return data[riskProfile as keyof typeof data] || data.Conservative
}

interface CompositionTableProps {
  riskProfile: "Passive" | "Conservative" | "Aggressive"
}

export default function CompositionTable({ riskProfile }: CompositionTableProps) {
  const data = getCompositionData(riskProfile)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left py-3 px-4 font-semibold text-muted-foreground text-xs uppercase tracking-wide">
              자산
            </th>
            <th className="text-left py-3 px-4 font-semibold text-muted-foreground text-xs uppercase tracking-wide">
              할당 비중
            </th>
            <th className="text-left py-3 px-4 font-semibold text-muted-foreground text-xs uppercase tracking-wide">
              예상 수익률
            </th>
            <th className="text-left py-3 px-4 font-semibold text-muted-foreground text-xs uppercase tracking-wide">
              리스크
            </th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={idx} className="border-b border-border hover:bg-muted/30 transition-colors">
              <td className="py-3 px-4 text-foreground font-medium">{row.asset}</td>
              <td className="py-3 px-4 text-foreground font-semibold">{row.allocation}</td>
              <td className="py-3 px-4 text-primary font-medium">{row.return}</td>
              <td
                className={`py-3 px-4 font-semibold text-xs uppercase tracking-wide ${
                  row.risk === "Low"
                    ? "text-green-600 dark:text-green-400"
                    : row.risk === "Medium"
                      ? "text-yellow-600 dark:text-yellow-400"
                      : row.risk === "High"
                        ? "text-orange-600 dark:text-orange-400"
                        : "text-red-600 dark:text-red-400"
                }`}
              >
                {row.risk}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

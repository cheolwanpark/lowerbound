"use client"

import { useState } from "react"
import { ChevronDown, TrendingUp, BarChart3, PieChart, AlertCircle } from "lucide-react"
import PayoffChart from "@/components/charts/payoff-chart"
import CompositionTable from "@/components/tables/composition-table"
import StressAnalysis from "@/components/charts/stress-analysis"
import AnalysisDetails from "@/components/sections/analysis-details"

interface PortfolioResponseProps {
  riskProfile: "Passive" | "Conservative" | "Aggressive"
  targetReturn: number
  maxDrawdown: number
}

export default function PortfolioResponse({ riskProfile, targetReturn, maxDrawdown }: PortfolioResponseProps) {
  const [showDetails, setShowDetails] = useState(false)

  const descriptions = {
    Passive: `안정적인 포트폴리오입니다. 주로 선물옵션의 기초자산을 장기 보유하며, 변동성 관리를 위해 Put 옵션으로 보호합니다.`,
    Conservative: `보수적인 포트폴리오입니다. 균형잡힌 수익률 추구와 리스크 관리를 함께 고려한 구성입니다.`,
    Aggressive: `공격적인 포트폴리오입니다. 높은 수익률을 추구하기 위해 Call 옵션과 스프레드 전략을 활용합니다.`,
  }

  return (
    <div className="space-y-3 max-w-4xl">
      {/* Portfolio Description */}
      <div className="bg-muted/50 border border-border rounded-lg p-4">
        <p className="text-sm text-foreground leading-relaxed">{descriptions[riskProfile]}</p>
      </div>

      {/* Payoff Chart */}
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-primary" />
          기초자산 가격 변동에 따른 수익률
        </h3>
        <PayoffChart riskProfile={riskProfile} />
      </div>

      {/* Composition Table */}
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <PieChart className="w-4 h-4 text-primary" />
          자산 구성
        </h3>
        <CompositionTable riskProfile={riskProfile} />
      </div>

      {/* Stress Analysis */}
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-primary" />
          스트레스 시나리오 분석
        </h3>
        <StressAnalysis riskProfile={riskProfile} targetReturn={targetReturn} />
      </div>

      {/* Toggle Details */}
      <button
        onClick={() => setShowDetails(!showDetails)}
        className="w-full flex items-center justify-between px-4 py-3 bg-muted/50 text-foreground hover:bg-muted transition-colors rounded-lg font-medium text-sm"
      >
        <span className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-muted-foreground" />
          상세 분석 보기
        </span>
        <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${showDetails ? "rotate-180" : ""}`} />
      </button>

      {showDetails && <AnalysisDetails riskProfile={riskProfile} />}
    </div>
  )
}

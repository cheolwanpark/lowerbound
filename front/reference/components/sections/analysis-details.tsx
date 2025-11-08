"use client"

import { BarChart3 } from "lucide-react"
import PerformanceSimulation from "@/components/charts/performance-simulation"

interface AnalysisDetailsProps {
  riskProfile: "Passive" | "Conservative" | "Aggressive"
}

const detailsContent = {
  Passive: {
    correlation: "BTC와 ETH의 상관관계는 높으나, Put Option을 통해 하방 리스크를 관리합니다.",
    rationale: "장기 투자자를 위한 보수적 구성으로, 기초자산의 장기 성장과 하방 보호를 동시에 추구합니다.",
  },
  Conservative: {
    correlation: "스팟 자산으로 기초 수익을 확보하고, Call Spread를 통해 추가 수익을 생성합니다.",
    rationale: "변동성을 활용한 추가 수익 창출과 리스크 관리의 균형을 맞춘 구성입니다.",
  },
  Aggressive: {
    correlation: "Call Option의 레버리지 효과로 높은 수익률을 추구합니다.",
    rationale: "단기 변동성을 최대한 활용하여 고수익을 목표로 하는 공격적인 포트폴리오입니다.",
  },
}

export default function AnalysisDetails({ riskProfile }: AnalysisDetailsProps) {
  const details = detailsContent[riskProfile as keyof typeof detailsContent]

  return (
    <div className="space-y-3">
      <div className="bg-card border border-border rounded-lg p-4">
        <h4 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-primary" />
          최근 데이터 시뮬레이션
        </h4>
        <PerformanceSimulation riskProfile={riskProfile} />
      </div>

      {/* Existing content sections */}
      <div className="bg-card border border-border rounded-lg p-4 space-y-3">
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">자산 간 역학관계</h4>
          <p className="text-sm text-muted-foreground">{details.correlation}</p>
        </div>
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-2">포트폴리오 근거</h4>
          <p className="text-sm text-muted-foreground">{details.rationale}</p>
        </div>
      </div>
    </div>
  )
}

"use client"

import { useState } from "react"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"

export function PresetForm() {
  const [strategy, setStrategy] = useState("conservative")
  const [targetAPY, setTargetAPY] = useState("10")
  const [maxDrawdown, setMaxDrawdown] = useState("15")

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Portfolio Preset</h3>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="strategy">Investment Strategy</Label>
          <Select value={strategy} onValueChange={setStrategy}>
            <SelectTrigger id="strategy" className="rounded-lg">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="passive">Passive</SelectItem>
              <SelectItem value="conservative">Conservative</SelectItem>
              <SelectItem value="aggressive">Aggressive</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="apy">Target APY (%)</Label>
          <Input
            id="apy"
            type="number"
            value={targetAPY}
            onChange={(e) => setTargetAPY(e.target.value)}
            className="rounded-lg"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="drawdown">Maximum Drawdown (%)</Label>
          <Input
            id="drawdown"
            type="number"
            value={maxDrawdown}
            onChange={(e) => setMaxDrawdown(e.target.value)}
            className="rounded-lg"
          />
        </div>
      </div>

      <div className="rounded-lg bg-muted p-3 text-xs text-muted-foreground">
        <p>설정을 변경하면 새로운 포트폴리오 버전이 생성됩니다.</p>
      </div>
    </div>
  )
}

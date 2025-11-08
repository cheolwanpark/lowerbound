interface PortfolioVersionTagProps {
  version: string
}

export function PortfolioVersionTag({ version }: PortfolioVersionTagProps) {
  return (
    <div className="ml-11 mt-2 inline-flex items-center gap-2 rounded-lg bg-primary/20 px-3 py-1 text-xs font-medium text-primary">
      <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />새 버전 생성됨 ({version})
    </div>
  )
}

/**
 * Financial Terms Glossary
 * Comprehensive definitions for all financial and crypto terms used in the UI
 */

export interface TermDefinition {
  term: string
  definition: string
  additionalInfo?: string
}

export const FINANCIAL_TERMS: Record<string, TermDefinition> = {
  // Portfolio Metrics
  apy: {
    term: "APY",
    definition: "Annual Percentage Yield - The expected yearly return on investment expressed as a percentage.",
    additionalInfo: "For example, an APY of 10% means a $1,000 investment would grow to $1,100 after one year.",
  },
  target_apy: {
    term: "Target APY",
    definition: "Your desired annual return goal for the portfolio.",
    additionalInfo: "The agent will attempt to construct a portfolio that achieves this target while managing risk.",
  },
  drawdown: {
    term: "Drawdown",
    definition: "The decline from a peak to a trough in portfolio value, measured as a percentage.",
    additionalInfo: "A drawdown of 20% means the portfolio fell from $10,000 to $8,000 from its highest point.",
  },
  max_drawdown: {
    term: "Maximum Drawdown",
    definition: "The largest peak-to-trough decline the portfolio should tolerate.",
    additionalInfo: "This is your maximum acceptable loss threshold. Lower values mean more conservative risk management.",
  },

  // Delta & Exposure
  delta: {
    term: "Delta",
    definition: "A measure of directional market exposure - how much your portfolio value changes with market movement.",
    additionalInfo: "Delta-neutral portfolios (~0 delta) aim to profit regardless of market direction through balanced long/short positions.",
  },
  delta_normalized: {
    term: "Delta Normalized",
    definition: "Delta scaled to a -1 to +1 range relative to portfolio size.",
    additionalInfo: "Values near 0 indicate neutral positioning. Positive values indicate net long exposure, negative indicates net short.",
  },
  delta_raw: {
    term: "Raw Delta",
    definition: "The absolute dollar amount of directional exposure in your portfolio.",
  },
  directional_exposure: {
    term: "Directional Exposure",
    definition: "The percentage of portfolio value exposed to market direction.",
    additionalInfo: "Higher percentages mean the portfolio is more sensitive to market movements.",
  },

  // Risk Metrics
  health_score: {
    term: "Health Score",
    definition: "A composite metric (0-100) evaluating overall portfolio safety and stability.",
    additionalInfo: "Scores above 80 are excellent, 60-80 are good, and below 60 indicate elevated risk.",
  },
  volatility: {
    term: "Volatility",
    definition: "A measure of how much asset prices fluctuate over time.",
    additionalInfo: "Higher volatility means larger and more frequent price swings, indicating higher risk.",
  },
  sharpe_ratio: {
    term: "Sharpe Ratio",
    definition: "A measure of risk-adjusted return - how much return you earn per unit of risk taken.",
    additionalInfo: "Higher Sharpe ratios indicate better risk-adjusted performance. A ratio above 1.0 is generally considered good.",
  },
  risk_contribution: {
    term: "Risk Contribution",
    definition: "How much each asset contributes to the total portfolio risk.",
    additionalInfo: "Even small positions can contribute significant risk if they are highly volatile or correlated.",
  },
  diversification_benefit: {
    term: "Diversification Benefit",
    definition: "The risk reduction achieved by holding multiple uncorrelated assets.",
    additionalInfo: "Higher percentages mean your assets balance each other better, reducing overall portfolio risk.",
  },

  // Liquidation & Leverage
  liquidation: {
    term: "Liquidation",
    definition: "The forced closure of a leveraged position when collateral falls below required levels.",
    additionalInfo: "This happens automatically to protect lenders. You lose your collateral when liquidated.",
  },
  liquidation_risk: {
    term: "Liquidation Risk",
    definition: "The probability that leveraged positions will be forcibly closed due to price movements.",
  },
  liquidation_price: {
    term: "Liquidation Price",
    definition: "The price level at which a leveraged position will be automatically closed.",
    additionalInfo: "Monitor this carefully - if the market price reaches this level, your position will be liquidated.",
  },
  leverage: {
    term: "Leverage",
    definition: "Using borrowed capital to increase position size and potential returns.",
    additionalInfo: "2x leverage means $1,000 controls $2,000 worth of assets. This amplifies both gains AND losses.",
  },

  // Portfolio Management
  rebalancing: {
    term: "Rebalancing",
    definition: "The process of realigning portfolio weights to maintain target allocations.",
    additionalInfo: "As prices change, your actual allocations drift from targets. Rebalancing restores the intended balance.",
  },
  sensitivity: {
    term: "Sensitivity",
    definition: "How portfolio value changes in response to price movements.",
    additionalInfo: "Sensitivity analysis shows the range of potential outcomes under different market scenarios.",
  },
  portfolio_value: {
    term: "Portfolio Value",
    definition: "The total current market value of all positions combined.",
  },

  // Investment Strategies
  strategy_passive: {
    term: "Passive Strategy",
    definition: "Low-risk, buy-and-hold approach with minimal active trading.",
    additionalInfo: "Focuses on stable assets with lower volatility and modest returns.",
  },
  strategy_conservative: {
    term: "Conservative Strategy",
    definition: "Moderate risk approach balancing stability with growth.",
    additionalInfo: "Uses limited leverage and maintains diversification across asset classes.",
  },
  strategy_aggressive: {
    term: "Aggressive Strategy",
    definition: "High-risk, high-return approach using leverage and concentrated positions.",
    additionalInfo: "Seeks maximum returns but exposes the portfolio to larger drawdowns and volatility.",
  },

  // Position Types
  spot: {
    term: "Spot Position",
    definition: "Direct ownership of an asset at current market price.",
    additionalInfo: "No leverage, no expiration - you own the actual cryptocurrency.",
  },
  futures: {
    term: "Futures Position",
    definition: "A derivative contract to buy/sell an asset at a predetermined price in the future.",
    additionalInfo: "Often used with leverage. Can be long (betting on price increase) or short (betting on decrease).",
  },
  lending_supply: {
    term: "Lending Supply",
    definition: "Assets you've supplied to a lending protocol to earn interest.",
    additionalInfo: "Your crypto is lent to borrowers, and you earn interest (APY) in return.",
  },
  lending_borrow: {
    term: "Lending Borrow",
    definition: "Assets you've borrowed from a lending protocol by providing collateral.",
    additionalInfo: "You pay interest and must maintain sufficient collateral to avoid liquidation.",
  },
  borrow_variable: {
    term: "Variable Rate",
    definition: "Interest rate that changes based on market supply and demand.",
    additionalInfo: "Can be lower during low demand but increases when borrowing is popular.",
  },
  borrow_stable: {
    term: "Stable Rate",
    definition: "Fixed interest rate that stays constant over the loan period.",
    additionalInfo: "Provides predictability but is typically higher than variable rates.",
  },

  // DeFi & Technical
  smart_contract: {
    term: "Smart Contract",
    definition: "Self-executing code on the blockchain that automatically manages financial operations.",
    additionalInfo: "No intermediaries needed - the code enforces all rules and executes transactions automatically.",
  },
  defi: {
    term: "DeFi",
    definition: "Decentralized Finance - blockchain-based financial services without traditional intermediaries.",
    additionalInfo: "Enables lending, borrowing, and trading directly between users through smart contracts.",
  },
  position: {
    term: "Position",
    definition: "A single investment holding within your portfolio.",
    additionalInfo: "Each position specifies the asset, quantity, type (spot/futures/lending), and entry details.",
  },
}

/**
 * Get term definition by key
 */
export function getTermDefinition(key: string): TermDefinition | undefined {
  return FINANCIAL_TERMS[key]
}

/**
 * Check if a term exists in the glossary
 */
export function hasTerm(key: string): boolean {
  return key in FINANCIAL_TERMS
}

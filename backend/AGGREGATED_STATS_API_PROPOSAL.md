# Aggregated Statistics API for AI Agents - Design Proposal

## Problem Statement

AI agents struggle with long time series data due to token limits and context overhead. Solution: Pre-aggregated statistics in compact, actionable format.

**Token Savings**: 80-85% reduction (from ~10k to ~2k tokens for 5 assets)

---

## API Endpoints

```
GET /api/v1/aggregated-stats/{asset}
GET /api/v1/aggregated-stats/multi?assets=BTC,ETH,SOL
```

**Query Parameters:**
- `start`, `end`: ISO 8601 datetime (required)
- `data_types`: "spot,futures,lending" (optional, default: all)

---

## Core Metrics (Curated for AI Agents)

### SPOT MARKET (12 metrics)

```json
{
  "spot": {
    "price": {
      "current": 46000.00,
      "min": 42000.00,
      "max": 48500.00,
      "mean": 45234.56
    },
    "returns": {
      "total_return_pct": 12.5,          // Period return
      "volatility_pct": 3.2,             // Annualized
      "sharpe_ratio": 1.8,               // Risk-adjusted return
      "max_drawdown_pct": -8.5           // Worst decline
    },
    "trend": {
      "direction": "bullish",            // bullish/bearish/neutral
      "momentum_7d_pct": 8.5,            // Recent momentum
      "days_up": 18,                     // vs 12 down
      "strength_score": 7.5              // 0-10 scale
    }
  }
}
```

---

### FUTURES MARKET (13 metrics)

```json
{
  "futures": {
    "funding": {
      "current_rate_pct": 0.01,          // Current 8h funding
      "mean_rate_pct": 0.01,             // Period average
      "cumulative_cost_pct": 0.45,       // Total funding paid
      "extreme_events": 2,               // |rate| > 0.1%
      "sentiment": "bullish"             // Based on funding pattern
    },
    "basis": {
      "current_premium_pct": 0.8,        // (mark - spot) / spot
      "mean_premium_pct": 0.5,
      "contango_ratio": 0.93             // Days in contango / total
    },
    "open_interest": {
      "current": 13200000,               // USD
      "change_pct": 15.6,                // Period change
      "trend": "increasing",             // increasing/decreasing/stable
      "leverage_signal": "high"          // low/medium/high
    },
    "risk_score": 6.5                    // 0-10 (funding + OI extremes)
  }
}
```

---

### LENDING MARKET (10 metrics)

```json
{
  "lending": {
    "supply": {
      "current_apy_pct": 2.8,
      "mean_apy_pct": 2.5,
      "min_apy_pct": 1.8,
      "max_apy_pct": 4.2
    },
    "borrow": {
      "current_variable_apy_pct": 4.5,
      "mean_variable_apy_pct": 4.2
    },
    "metrics": {
      "spread_pct": 1.7,                 // Borrow - Supply
      "utilization_proxy": "medium",     // low/medium/high
      "yield_stability": 7.5,            // 0-10 (inverse volatility)
      "attractiveness_score": 6.5        // 0-10 (yield vs risk)
    }
  }
}
```

---

## Multi-Asset Response

```json
{
  "query": {
    "assets": ["BTC", "ETH", "SOL"],
    "start": "2025-01-01T00:00:00Z",
    "end": "2025-02-01T00:00:00Z",
    "period_days": 31
  },
  "data": {
    "BTC": {
      "spot": { /* 12 metrics */ },
      "futures": { /* 13 metrics */ },
      "lending": null
    },
    "ETH": { /* ... */ },
    "SOL": { /* ... */ }
  },
  "cross_asset": {
    "correlations": {
      "BTC_ETH": 0.85,
      "BTC_SOL": 0.72,
      "ETH_SOL": 0.78
    },
    "market_regime": "high_volatility",  // or low_volatility/trending/ranging
    "avg_volatility_pct": 3.8
  }
}
```

**Total Core Metrics**: 35 per asset (12 spot + 13 futures + 10 lending)

---

## Implementation Plan

### File Structure
```
src/analysis/aggregated_stats.py  (~300 lines)
  - calculate_spot_stats()
  - calculate_futures_stats()
  - calculate_lending_stats()
  - calculate_cross_asset_stats()

src/api.py  (~100 lines additions)
  - GET /aggregated-stats/{asset}
  - GET /aggregated-stats/multi
```

### Database Optimization (Optional)
```sql
-- Materialized view for faster daily aggregations
CREATE MATERIALIZED VIEW daily_spot_stats AS
SELECT
    asset,
    DATE_TRUNC('day', timestamp) as date,
    MIN(low) as min_price,
    MAX(high) as max_price,
    AVG(close) as avg_price,
    STDDEV(close) as std_dev
FROM spot_ohlcv
GROUP BY asset, date;

-- Refresh hourly
```

---

## Usage Examples

### Example 1: Quick Portfolio Decision
```python
stats = await get_aggregated_stats_single(
    asset="BTC",
    start="2025-01-01",
    end="2025-02-01"
)

# AI prompt: "Based on these stats, should I enter long?"
if (stats['spot']['trend']['direction'] == 'bullish' and
    stats['futures']['funding']['sentiment'] == 'bullish' and
    stats['spot']['returns']['sharpe_ratio'] > 1.5):
    decision = "ENTER_LONG"
```

### Example 2: Multi-Asset Comparison
```python
stats = await get_aggregated_stats_multi(
    assets="BTC,ETH,SOL",
    start="2025-01-15",
    end="2025-02-15"
)

# Find best risk-adjusted returns
best_asset = max(stats['data'].items(),
                 key=lambda x: x[1]['spot']['returns']['sharpe_ratio'])
```

### Example 3: Lending vs Holding
```python
stats = await get_aggregated_stats_single(asset="WETH", ...)

lending_apy = stats['lending']['supply']['current_apy_pct']
price_volatility = stats['spot']['returns']['volatility_pct']

if lending_apy > 2.0 and price_volatility < 5.0:
    decision = "SUPPLY_TO_LENDING"  # Stable yield opportunity
```

---

## Key Benefits

1. **Token Efficiency**: 35 metrics vs 60+ raw data points
2. **Actionable Insights**: Pre-calculated risk scores, sentiment, trends
3. **Fast Reasoning**: Clear semantic labels (bullish/bearish vs raw numbers)
4. **Production Ready**: Cacheable, <500ms response time

---

## Metric Selection Rationale

### What's INCLUDED ✅
- **Price extremes** (min/max) - Critical support/resistance
- **Returns & volatility** - Core risk metrics
- **Sharpe ratio** - Risk-adjusted performance (gold standard)
- **Trend direction** - Semantic clarity for AI
- **Funding rate** - Futures sentiment indicator
- **Open Interest** - Leverage and liquidity proxy
- **Spread (lending)** - Utilization and opportunity cost

### What's EXCLUDED ❌
- **OHLC details** - Available in raw endpoint
- **Median prices** - Mean sufficient for most decisions
- **Volume stats** - Less critical for portfolio decisions
- **Intraday patterns** - Not needed for strategic decisions
- **Multiple percentiles** - Keep it simple

---

## Timeline & Effort

- **Core implementation**: ~400 lines, 1 day
- **Testing**: 0.5 days
- **Documentation**: 0.5 days
- **Total**: 2 days

---

## Success Criteria

- Response time: <500ms (single), <2s (5 assets)
- Token reduction: >80% vs raw data
- Cache hit rate: >70%
- Accuracy: <1% error vs ground truth calculations

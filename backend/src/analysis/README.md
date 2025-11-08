# Risk Profile Analysis Module

Comprehensive risk analysis for cryptocurrency portfolios containing spot and futures positions.

## Features

- **Portfolio Valuation**: Calculate current and projected portfolio values
- **Sensitivity Analysis**: Analyze portfolio response to price changes (-30% to +30%)
- **Risk Metrics**:
  - Value at Risk (VaR) at 95% and 99% confidence levels
  - Conditional VaR (CVaR / Expected Shortfall)
  - Portfolio volatility (annualized)
  - Sharpe ratio
  - Maximum drawdown
  - Delta exposure (market directional risk)
  - Asset correlation matrix
- **Scenario Analysis**: 8 predefined market scenarios (bull/bear markets, crypto winter, etc.)

## Module Structure

```
src/analysis/
├── __init__.py           # Package initialization
├── data_service.py       # Historical data fetching and alignment (~150 lines)
├── valuation.py          # Position valuation logic (~100 lines)
├── metrics.py            # Risk metrics calculations (~150 lines)
├── scenarios.py          # Scenario definitions and execution (~80 lines)
├── riskprofile.py        # Main orchestration module (~120 lines)
└── README.md             # This file
```

## API Endpoint

### POST `/api/v1/analysis/risk-profile`

Calculate comprehensive risk profile for a portfolio.

**Request Body:**

```json
{
  "positions": [
    {
      "asset": "BTC",
      "quantity": 1.5,
      "position_type": "spot",
      "entry_price": 45000.0,
      "leverage": 1.0
    },
    {
      "asset": "ETH",
      "quantity": 10.0,
      "position_type": "futures_long",
      "entry_price": 2500.0,
      "leverage": 3.0
    }
  ],
  "lookback_days": 30
}
```

**Position Types:**
- `spot`: Spot position (long only)
- `futures_long`: Futures long position with leverage
- `futures_short`: Futures short position with leverage

**Parameters:**
- `positions`: List of 1-20 portfolio positions
- `lookback_days`: Historical data lookback period (7-180 days, default: 30)

**Response:**

```json
{
  "current_portfolio_value": 117500.0,
  "data_availability_warning": "Warning: Only 28 days of data available...",
  "sensitivity_analysis": [
    {
      "price_change_pct": -30,
      "portfolio_value": 82250.0,
      "pnl": -35250.0,
      "return_pct": -30.0
    },
    ...
  ],
  "risk_metrics": {
    "lookback_days_used": 28,
    "portfolio_variance": 0.0025,
    "portfolio_volatility_annual": 0.27,
    "var_95_1day": -3500.0,
    "var_99_1day": -5200.0,
    "cvar_95": -4100.0,
    "sharpe_ratio": 1.23,
    "max_drawdown": -0.18,
    "delta_exposure": 31.5,
    "correlation_matrix": {
      "BTC": {"BTC": 1.0, "ETH": 0.85},
      "ETH": {"BTC": 0.85, "ETH": 1.0}
    }
  },
  "scenarios": [
    {
      "name": "Bull Market (+30%)",
      "description": "All assets increase by 30%",
      "portfolio_value": 152750.0,
      "pnl": 35250.0,
      "return_pct": 30.0
    },
    ...
  ]
}
```

## Methodology

### VaR/CVaR Calculation
- **Method**: Historical Simulation (non-parametric)
- **Time Horizon**: 1-day
- **Confidence Levels**: 95%, 99%
- Based on actual portfolio return distribution from historical data

### Volatility & Sharpe Ratio
- **Calculation**: Standard deviation of daily log returns
- **Annualization**: σ_annual = σ_daily × √365
- **Sharpe Ratio**: (mean_return - risk_free_rate) / volatility
- **Risk-Free Rate**: 0% (configurable in settings)

### Time Series Alignment
- **Spot Data**: 12-hour OHLCV candles resampled to daily (last close price)
- **Futures Data**: 8-hour mark prices and funding rates resampled to daily
- **Gap Handling**: Forward-fill for gaps ≤2 days, warning for longer gaps
- **Alignment**: All time series aligned to common daily timestamps

### Position Valuation

**Spot Position:**
```
Value = Quantity × Current_Price
```

**Futures Long:**
```
Margin = (Quantity × Entry_Price) / Leverage
PnL = (Current_Price - Entry_Price) × Quantity × Leverage
Value = Margin + PnL
```

**Futures Short:**
```
Margin = (Quantity × Entry_Price) / Leverage
PnL = (Entry_Price - Current_Price) × Quantity × Leverage
Value = Margin + PnL
```

### Delta Exposure
```
Delta = Σ(spot quantities) + Σ(futures_long × leverage) - Σ(futures_short × leverage)
```

- **Delta = 0**: Market-neutral position
- **Delta > 0**: Net long exposure
- **Delta < 0**: Net short exposure

## Predefined Scenarios

1. **Bull Market (+30%)**: All assets increase by 30%
2. **Bear Market (-30%)**: All assets decrease by 30%
3. **Crypto Winter (-50%)**: Severe bear market
4. **Moderate Rally (+15%)**: Moderate upward movement
5. **Flash Crash (-20%)**: Sudden sharp decline
6. **BTC Dominance**: BTC +40%, other assets -10%
7. **Alt Season**: ETH/SOL +50%, BTC +20%
8. **Risk-Off Environment**: BTC -15%, altcoins -35%

## Configuration

Settings in `src/config.py`:

```python
RISK_ANALYSIS_DEFAULT_LOOKBACK_DAYS = 30  # Default lookback period
RISK_ANALYSIS_MAX_LOOKBACK_DAYS = 180     # Maximum lookback period
FUNDING_RATE_LOOKBACK_DAYS = 30            # Funding rate data availability
MAX_PORTFOLIO_POSITIONS = 20               # Maximum positions per portfolio
MAX_LEVERAGE_LIMIT = 125.0                 # Maximum leverage allowed
SENSITIVITY_RANGE = [-30, -25, ..., 30]    # Price shock range (%)
VAR_CONFIDENCE_LEVELS = [0.95, 0.99]       # VaR confidence levels
RISK_FREE_RATE = 0.0                       # Annual risk-free rate
```

## Limitations

1. **Data Availability**:
   - Funding rate data only available for past 30 days
   - Spot data can go back 180 days
   - Inconsistent lookback windows may affect accuracy

2. **Assumptions**:
   - Basis (futures-spot spread) remains constant during price shocks
   - No slippage or transaction costs considered
   - No liquidation modeling (assumes sufficient margin)

3. **Time Resolution**:
   - Daily intervals only (12h spot and 8h futures resampled to 24h)
   - Not suitable for intraday risk analysis

4. **VaR Limitations**:
   - Historical simulation assumes past patterns repeat
   - May underestimate tail risk in crypto markets
   - Small sample sizes (30 days = ~30 observations) reduce accuracy

## Usage Examples

### Python SDK

```python
from src.models import PositionInput, RiskProfileRequest
from src.analysis.riskprofile import calculate_risk_profile

# Define portfolio
positions = [
    PositionInput(
        asset="BTC",
        quantity=1.5,
        position_type="spot",
        entry_price=45000.0
    ),
    PositionInput(
        asset="ETH",
        quantity=10.0,
        position_type="futures_long",
        entry_price=2500.0,
        leverage=3.0
    )
]

request = RiskProfileRequest(
    positions=positions,
    lookback_days=30
)

# Calculate risk profile
result = await calculate_risk_profile(request.model_dump())

print(f"Portfolio Value: ${result['current_portfolio_value']:,.2f}")
print(f"VaR (95%): ${result['risk_metrics']['var_95_1day']:,.2f}")
```

### cURL

```bash
curl -X POST http://localhost:8000/api/v1/analysis/risk-profile \
  -H "Content-Type: application/json" \
  -d '{
    "positions": [
      {
        "asset": "BTC",
        "quantity": 1.5,
        "position_type": "spot",
        "entry_price": 45000.0,
        "leverage": 1.0
      }
    ],
    "lookback_days": 30
  }'
```

## Testing

Run the test suite:

```bash
python test_risk_profile.py
```

**Requirements:**
- PostgreSQL database running
- Database schema initialized
- Historical data available for tested assets (BTC, ETH, SOL)
- At least 30 days of data

## Dependencies

- `pandas`: Time series manipulation and resampling
- `numpy`: Numerical computations (returns, statistics)
- `asyncpg`: Async database queries (via `src.database`)
- `pydantic`: Request/response validation
- `loguru`: Logging

## Performance Considerations

- **Query Optimization**: Concurrent data fetching for multiple assets
- **Time Complexity**: O(n×m) where n=lookback_days, m=positions
- **Typical Response Time**: 1-3 seconds for 30-day lookback, 3 positions
- **Bottleneck**: Database queries (especially for 180-day lookback)

**Recommendations:**
- Use 30-day lookback for real-time analysis
- Cache results for frequently-queried portfolios
- Consider pagination for large sensitivity tables

## Future Enhancements

1. **Advanced Metrics**:
   - Sortino ratio (downside deviation)
   - Information ratio
   - Calmar ratio
   - Beta vs. market index

2. **Monte Carlo Simulation**:
   - Parametric VaR using simulated returns
   - Stress testing with extreme scenarios

3. **Liquidation Modeling**:
   - Margin call thresholds
   - Liquidation price calculations
   - Cascading liquidation scenarios

4. **Optimization**:
   - Portfolio optimization (efficient frontier)
   - Risk-adjusted position sizing
   - Hedging recommendations

5. **Real-Time Updates**:
   - WebSocket streaming of risk metrics
   - Alert system for VaR breaches
   - Periodic rebalancing suggestions

## License

Part of the crypto-portfolio project.

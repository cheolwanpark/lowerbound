"""Risk profile calculation tool for portfolio analysis."""

import json
from typing import Annotated, Any, Dict

from src.agent.models import ToolContext
from src.agent.tools._validation import (
    MIN_LOOKBACK_DAYS,
    MAX_LOOKBACK_DAYS,
    MIN_POSITIONS,
    MAX_POSITIONS,
    validate_position,
)
from src.wrapper import BaseTool, tool


class RiskProfileTools(BaseTool):
    """Tools for calculating portfolio risk metrics."""

    tool_server_name = "portfolio_advisor_risk"
    tool_server_version = "1.0.0"

    def __init__(self, context: ToolContext) -> None:
        """Initialize risk profile tools with shared context.

        Args:
            context: Tool context with chat_id, backend_client, and portfolio state
        """
        self.context = context
        super().__init__()

    @tool()
    async def calculate_risk_profile(
        self,
        positions_json: Annotated[
            str,
            """JSON array of position objects. Each position must have:
- asset (str): Asset symbol (e.g., 'BTC', 'ETH', 'WETH', 'USDC')
- quantity (float): Position size, must be > 0
- position_type (str): One of 'spot', 'futures_long', 'futures_short', 'lending_supply', 'lending_borrow'
- entry_price (float): Entry price in USD (required for spot/futures, ignored for lending)
- leverage (float, optional): 1.0-125.0, default 1.0 (for futures only)
- entry_timestamp (str, optional): ISO 8601 timestamp for lending positions
- borrow_type (str, optional): 'variable' or 'stable' for lending_borrow

Example: [{"asset": "BTC", "quantity": 1.5, "position_type": "spot", "entry_price": 45000.0, "leverage": 1.0}]""",
        ],
        lookback_days: Annotated[
            int,
            "Historical lookback period in days (7-180). Default: 30. Used to calculate historical volatility, correlations, VaR.",
        ] = 30,
    ) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics for a portfolio.

        Use this to analyze the risk characteristics of a portfolio including VaR,
        volatility, Sharpe ratio, stress test scenarios, and lending metrics.

        Returns JSON with comprehensive risk analysis including:
        - current_portfolio_value: Total portfolio value in USD
        - sensitivity_analysis: Portfolio value at various price changes (-30% to +30%)
        - risk_metrics: volatility, VaR (95%, 99%), CVaR, Sharpe ratio, max drawdown,
          correlation matrix
        - scenarios: 8 predefined market scenarios (bull, bear, flash crash, etc.)
        - lending_metrics: If lending positions exist - LTV, health factor,
          net APY, liquidation risk
        """
        # Parse JSON
        try:
            positions = json.loads(positions_json)
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON syntax: {str(e)}",
                "hint": "Ensure positions_json is a valid JSON array. Check for missing commas, quotes, or brackets.",
                "example": '[{"asset": "BTC", "quantity": 1.5, "position_type": "spot", "entry_price": 45000.0}]'
            }

        # Validate basic structure
        if not isinstance(positions, list):
            return {
                "error": f"positions_json must be a JSON array, got {type(positions).__name__}",
                "hint": "Wrap your position(s) in square brackets [...] even if there's only one position."
            }

        if len(positions) < MIN_POSITIONS:
            return {
                "error": f"At least {MIN_POSITIONS} position is required (got {len(positions)})",
                "hint": "Provide at least one position to analyze."
            }

        if len(positions) > MAX_POSITIONS:
            return {
                "error": f"Too many positions: {len(positions)} (max {MAX_POSITIONS} allowed)",
                "hint": "Split large portfolios into smaller groups or focus on the most significant positions."
            }

        # Validate lookback_days range
        if not (MIN_LOOKBACK_DAYS <= lookback_days <= MAX_LOOKBACK_DAYS):
            return {
                "error": f"lookback_days must be between {MIN_LOOKBACK_DAYS} and {MAX_LOOKBACK_DAYS} (got {lookback_days})",
                "hint": "For portfolios with futures positions, use lookback_days ≤ 30 due to data availability limits."
            }

        # Validate each position
        for i, position in enumerate(positions, start=1):
            error = validate_position(position, i)
            if error:
                return {
                    "error": error,
                    "position_index": i,
                    "provided_position": position,
                    "hint": "Check the BACKEND API REFERENCE section in your system prompt for required fields per position type."
                }

        # Check if any futures positions exist and warn if lookback is > 30 days
        has_futures = any(
            p.get("position_type") in ("futures_long", "futures_short")
            for p in positions
        )
        if has_futures and lookback_days > 30:
            return {
                "error": f"Portfolio contains futures positions but lookback_days={lookback_days} exceeds data availability",
                "hint": "Futures funding rate data is only available for ~30 days. Use lookback_days ≤ 30 for portfolios with futures positions.",
                "affected_positions": [
                    i+1 for i, p in enumerate(positions)
                    if p.get("position_type") in ("futures_long", "futures_short")
                ]
            }

        try:
            # Call backend
            result = await self.context.backend_client.calculate_risk_profile(
                positions=positions,
                lookback_days=lookback_days,
            )

            return result

        except Exception as e:
            # Extract 'detail' field from HTTP error response
            import httpx

            error_detail = str(e)
            if isinstance(e, httpx.HTTPStatusError):
                try:
                    error_json = e.response.json()
                    if 'detail' in error_json:
                        error_detail = error_json['detail']
                except:
                    pass

            return {
                "error": f"Backend API error: {error_detail}",
                "requested_positions_count": len(positions),
                "requested_lookback_days": lookback_days,
                "hint": "Check the error message above. The backend may be unable to calculate risk for this portfolio."
            }

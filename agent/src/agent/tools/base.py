"""Unified portfolio advisory tools using BaseTool pattern."""

import json
from typing import Annotated, Any, Dict

from src.agent.models import ToolContext
from src.models import PortfolioPosition
from src.wrapper import BaseTool, tool


class PortfolioTools(BaseTool):
    """Complete tool collection for crypto portfolio risk advisory.

    Provides tools for historical data analysis, risk profiling, and
    portfolio management using the MCP BaseTool pattern.
    """

    tool_server_name = "portfolio_advisor"
    tool_server_version = "1.0.0"

    def __init__(self, context: ToolContext) -> None:
        """Initialize portfolio tools with shared context.

        Args:
            context: Tool context with chat_id, backend_client, and portfolio state
        """
        self.context = context
        super().__init__()

    # Historical Data Tools

    @tool()
    async def get_aggregated_stats(
        self,
        assets: Annotated[
            str,
            "Single asset symbol (e.g., 'BTC') or comma-separated list (e.g., 'BTC,ETH,SOL') for multiple assets. Max 10 assets.",
        ],
        start_date: Annotated[
            str,
            "Start date in ISO 8601 UTC format (e.g., '2025-01-01T00:00:00Z'). Max 90 days from end_date.",
        ],
        end_date: Annotated[
            str,
            "End date in ISO 8601 UTC format (e.g., '2025-02-01T00:00:00Z')",
        ],
        data_types: Annotated[
            str,
            "Comma-separated data types to include. Options: 'spot', 'futures', 'lending'. Default: 'spot,futures'",
        ] = "spot,futures",
    ) -> Dict[str, Any]:
        """Fetch aggregated statistics for crypto assets from the backend API.

        Use this to get historical price data, volatility, returns, funding rates,
        lending rates, and other aggregated metrics for analysis.

        Returns JSON with aggregated statistics including:
        - Spot stats: current_price, min/max/mean price, total return, volatility,
          Sharpe ratio, max drawdown
        - Futures stats: funding rates, basis premium, open interest
        - Lending stats: supply/borrow APY, spread
        - Correlation matrix (for multiple assets)
        """
        try:
            # Parse inputs
            asset_list = assets.split(",") if "," in assets else assets
            data_type_list = data_types.split(",")

            # Call backend
            result = await self.context.backend_client.get_aggregated_stats(
                assets=asset_list,
                start_date=start_date,
                end_date=end_date,
                data_types=data_type_list,
            )

            return result

        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to fetch aggregated stats. Check your parameters.",
            }

    # Risk Profile Tools

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
        try:
            # Parse positions
            positions = json.loads(positions_json)

            # Validate basic structure
            if not isinstance(positions, list):
                return {
                    "error": "positions_json must be a JSON array",
                }

            if len(positions) == 0:
                return {
                    "error": "At least one position is required",
                }

            if len(positions) > 20:
                return {
                    "error": "Maximum 20 positions allowed",
                }

            # Call backend
            result = await self.context.backend_client.calculate_risk_profile(
                positions=positions,
                lookback_days=lookback_days,
            )

            return result

        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON: {str(e)}",
                "message": "positions_json must be valid JSON array",
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to calculate risk profile. Check your position format.",
            }

    # Portfolio Management Tools

    @tool()
    async def set_portfolio(
        self,
        positions_json: Annotated[
            str,
            """JSON array of position objects. Same format as calculate_risk_profile.
Each position must have: asset, quantity, position_type, entry_price,
leverage (optional), and lending-specific fields if applicable.

Example: [
    {"asset": "BTC", "quantity": 0.5, "position_type": "spot", "entry_price": 45000.0},
    {"asset": "ETH", "quantity": 5.0, "position_type": "futures_long", "entry_price": 2500.0, "leverage": 2.0}
]""",
        ],
        explanation: Annotated[
            str,
            "Clear explanation of WHY you're recommending this portfolio composition. Include reasoning about risk/return trade-offs, diversification, and how it meets the user's constraints.",
        ],
    ) -> Dict[str, Any]:
        """Update the portfolio recommendation for this chat.

        Call this when you have a portfolio recommendation to make. The portfolio
        will be stored and visible to the user immediately.
        """
        try:
            # Parse and validate positions
            positions_data = json.loads(positions_json)

            if not isinstance(positions_data, list):
                return {
                    "success": False,
                    "error": "positions_json must be a JSON array",
                }

            if len(positions_data) == 0:
                return {
                    "success": False,
                    "error": "At least one position is required",
                }

            # Validate using Pydantic models
            positions = [PortfolioPosition(**p) for p in positions_data]

            # Update context (will be committed by worker atomically)
            self.context.current_portfolio = positions
            self.context.reasonings.append(f"Portfolio Update: {explanation}")

            return {
                "success": True,
                "positions_count": len(positions),
                "message": f"Portfolio updated with {len(positions)} position(s)",
                "explanation": explanation,
            }

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON: {str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to set portfolio. Check position format.",
            }

    @tool()
    async def get_current_portfolio(self) -> Dict[str, Any]:
        """Get the current portfolio for this chat.

        Use this to check what portfolio is currently recommended before making updates.
        """
        if self.context.current_portfolio:
            positions_data = [p.model_dump() for p in self.context.current_portfolio]
            return {
                "has_portfolio": True,
                "positions": positions_data,
                "count": len(positions_data),
            }
        else:
            return {
                "has_portfolio": False,
                "message": "No portfolio has been set yet",
            }

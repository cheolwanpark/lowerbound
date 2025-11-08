"""Historical data retrieval tool for crypto assets."""

import logging
from typing import Annotated, Any, Dict

from src.agent.models import ToolContext
from src.agent.tools._validation import validate_asset, validate_date_format
from src.wrapper import BaseTool, tool

logger = logging.getLogger(__name__)


class HistoricalDataTools(BaseTool):
    """Tools for fetching historical crypto market data."""

    tool_server_name = "portfolio_advisor_historical"
    tool_server_version = "1.0.0"

    def __init__(self, context: ToolContext) -> None:
        """Initialize historical data tools with shared context.

        Args:
            context: Tool context with chat_id, backend_client, and portfolio state
        """
        self.context = context
        super().__init__()

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
        # Parse inputs
        asset_list = [a.strip() for a in assets.split(",")] if "," in assets else [assets.strip()]
        data_type_list = [dt.strip() for dt in data_types.split(",")]

        logger.debug("get_aggregated_stats: assets=%s, dates=%s to %s", asset_list, start_date, end_date)

        # Validate assets
        for asset in asset_list:
            # Determine which asset list to check based on data types
            for data_type in data_type_list:
                if data_type in ("spot", "futures"):
                    error = validate_asset(asset, "spot")
                elif data_type == "lending":
                    error = validate_asset(asset, "lending")
                else:
                    continue

                if error:
                    return {
                        "error": error,
                        "hint": "Check the BACKEND API REFERENCE section in your system prompt for the complete list of available assets."
                    }

        # Validate max 10 assets
        if len(asset_list) > 10:
            return {
                "error": f"Too many assets: {len(asset_list)} (max 10 allowed)",
                "provided_assets": asset_list,
                "hint": "Split your request into multiple calls with ≤10 assets each."
            }

        # Validate date formats
        start_error = validate_date_format(start_date, "start_date")
        if start_error:
            return {
                "error": start_error,
                "hint": "Use ISO 8601 UTC format like '2025-01-01T00:00:00Z'. Include the 'T' separator and 'Z' timezone."
            }

        end_error = validate_date_format(end_date, "end_date")
        if end_error:
            return {
                "error": end_error,
                "hint": "Use ISO 8601 UTC format like '2025-01-01T00:00:00Z'. Include the 'T' separator and 'Z' timezone."
            }

        try:
            # Call backend
            result = await self.context.backend_client.get_aggregated_stats(
                assets=asset_list,
                start_date=start_date,
                end_date=end_date,
                data_types=data_type_list,
            )

            # Check if result contains any actual data
            data = result.get("data", {})
            if data:
                # Check if all assets have null/None stats
                all_null = all(
                    all(v is None for v in asset_data.values()) if isinstance(asset_data, dict) else True
                    for asset_data in data.values()
                )

                if all_null:
                    return {
                        "error": "No data available for the requested date range",
                        "requested_assets": asset_list,
                        "requested_date_range": f"{start_date} to {end_date}",
                        "requested_data_types": data_type_list,
                        "hint": "The database may not have data for this period. Try: 1) Check if the backend has completed initial backfill, 2) Use a more recent date range (e.g., last 30 days), 3) Verify the backend service is running and collecting data.",
                        "debug_response": result
                    }

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
                "requested_assets": asset_list,
                "requested_date_range": f"{start_date} to {end_date}",
                "hint": "Check the error message above and adjust your parameters accordingly."
            }

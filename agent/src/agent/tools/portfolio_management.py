"""Portfolio management tools for setting and retrieving portfolios."""

import json
from typing import Annotated, Any, Dict

from src.agent.models import ToolContext
from src.agent.tools._validation import (
    MIN_POSITIONS,
    MAX_POSITIONS,
    validate_position,
)
from src.models import PortfolioPosition
from src.wrapper import BaseTool, tool


class PortfolioManagementTools(BaseTool):
    """Tools for managing portfolio recommendations."""

    tool_server_name = "portfolio_advisor_management"
    tool_server_version = "1.0.0"

    def __init__(self, context: ToolContext) -> None:
        """Initialize portfolio management tools with shared context.

        Args:
            context: Tool context with chat_id, backend_client, and portfolio state
        """
        self.context = context
        super().__init__()

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
        # Parse JSON
        try:
            positions_data = json.loads(positions_json)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON syntax: {str(e)}",
                "hint": "Ensure positions_json is a valid JSON array. Check for missing commas, quotes, or brackets.",
                "example": '[{"asset": "BTC", "quantity": 0.5, "position_type": "spot", "entry_price": 45000.0}]'
            }

        # Validate basic structure
        if not isinstance(positions_data, list):
            return {
                "success": False,
                "error": f"positions_json must be a JSON array, got {type(positions_data).__name__}",
                "hint": "Wrap your position(s) in square brackets [...] even if there's only one position."
            }

        if len(positions_data) < MIN_POSITIONS:
            return {
                "success": False,
                "error": f"At least {MIN_POSITIONS} position is required (got {len(positions_data)})",
                "hint": "Provide at least one position to set the portfolio."
            }

        if len(positions_data) > MAX_POSITIONS:
            return {
                "success": False,
                "error": f"Too many positions: {len(positions_data)} (max {MAX_POSITIONS} allowed)",
                "hint": "Focus on the most significant positions or split into multiple portfolios."
            }

        # Validate each position before creating Pydantic models
        for i, position in enumerate(positions_data, start=1):
            error = validate_position(position, i)
            if error:
                return {
                    "success": False,
                    "error": error,
                    "position_index": i,
                    "provided_position": position,
                    "hint": "Check the BACKEND API REFERENCE section in your system prompt for required fields per position type."
                }

        # Validate using Pydantic models (this provides additional type checking)
        try:
            positions = [PortfolioPosition(**p) for p in positions_data]
        except Exception as e:
            return {
                "success": False,
                "error": f"Pydantic validation failed: {str(e)}",
                "hint": "The position structure is valid but field types or values don't match the schema. Check that all numeric fields are numbers, not strings."
            }

        # Validate explanation is not empty
        if not explanation or not explanation.strip():
            return {
                "success": False,
                "error": "explanation is required and must not be empty",
                "hint": "Provide a clear explanation of WHY you're recommending this portfolio. Include reasoning about risk/return trade-offs and how it meets user constraints."
            }

        # Update context (for agent's internal use)
        self.context.current_portfolio = positions
        # NOTE: Don't append to reasonings here - portfolio updates are tracked via portfolio_versions
        # and toolcalls, not as reasoning steps

        # Write to Redis IMMEDIATELY as new version for real-time visibility
        version_number = None
        try:
            record = self.context.chat_store.add_portfolio_version(
                chat_id=self.context.chat_id,
                portfolio=positions,
                explanation=explanation,
            )
            version_number = len(record.portfolio_versions)
        except Exception as e:
            # Log error but don't fail the tool call
            import logging
            logging.getLogger(__name__).error(
                f"Failed to write portfolio version to Redis: {e}"
            )

        return {
            "success": True,
            "positions_count": len(positions),
            "version": version_number,
            "message": f"Portfolio version {version_number} created with {len(positions)} position(s) (visible in real-time via GET API)",
            "explanation": explanation,
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

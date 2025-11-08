"""Agent tools for Claude Agent SDK."""

from src.agent.models import ToolContext
from src.agent.tools.historical_data import HistoricalDataTools
from src.agent.tools.portfolio_management import PortfolioManagementTools
from src.agent.tools.reasoning_step import ReasoningTools
from src.agent.tools.risk_profile import RiskProfileTools


class PortfolioTools(
    HistoricalDataTools,
    RiskProfileTools,
    PortfolioManagementTools,
    ReasoningTools,
):
    """Unified portfolio advisory tools combining all tool categories.

    This class aggregates tools from multiple specialized tool classes via multiple inheritance:
    - HistoricalDataTools: get_aggregated_stats
    - RiskProfileTools: calculate_risk_profile
    - PortfolioManagementTools: set_portfolio, get_current_portfolio
    - ReasoningTools: reasoning_step

    The BaseTool._discover_tools() method will automatically find all @tool() decorated
    methods from all parent classes via MRO (Method Resolution Order).
    """

    tool_server_name = "portfolio_advisor"
    tool_server_version = "1.0.0"

    def __init__(self, context: ToolContext) -> None:
        """Initialize all portfolio tools with shared context.

        Args:
            context: Tool context with chat_id, backend_client, and portfolio state
        """
        # Store context before calling parent __init__
        # This is needed because tool methods will access self.context
        self.context = context

        # Call BaseTool.__init__() which will discover all tools from parent classes
        # Note: We need to call the BaseTool init specifically to avoid MRO issues
        from src.wrapper import BaseTool
        BaseTool.__init__(self)


__all__ = ["PortfolioTools"]

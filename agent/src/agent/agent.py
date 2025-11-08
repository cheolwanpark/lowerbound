"""Chat agent implementation using Claude Agent SDK."""

import asyncio
from typing import Optional

from src.agent.models import AgentResult, ToolContext
from src.agent.prompt import (
    format_followup_prompt,
    format_initial_prompt,
    format_system_prompt,
)
from src.agent.tools import PortfolioTools
from src.backend_client import BackendClient
from src.config import Settings
from src.models import ChatCreateRequest, ChatMessage, ChatRecord
from src.storage.chat_store import ChatStore
from src.wrapper import Agent


class ChatAgent:
    """AI agent for portfolio risk advisory using Claude Agent SDK."""

    def __init__(
        self,
        settings: Settings,
        backend_client: BackendClient,
        chat_store: ChatStore,
    ):
        """Initialize chat agent.

        Args:
            settings: Application settings
            backend_client: Backend API client
            chat_store: ChatStore for direct Redis writes
        """
        self.settings = settings
        self.backend_client = backend_client
        self.chat_store = chat_store

    async def run_initial(
        self,
        chat_id: str,
        request: ChatCreateRequest,
        user_prompt: str,
    ) -> AgentResult:
        """Run agent for initial chat creation.

        Args:
            chat_id: Chat identifier
            request: Chat creation request with parameters
            user_prompt: User's initial message

        Returns:
            Agent result with messages and optional portfolio
        """
        # Create tool context
        context = ToolContext(
            chat_id=chat_id,
            backend_client=self.backend_client,
            chat_store=self.chat_store,
            current_portfolio=None,
        )

        # Format prompts
        system_prompt = format_system_prompt(
            request.strategy,
            request.target_apy,
            request.max_drawdown,
        )

        user_prompt_text = format_initial_prompt(
            request.strategy,
            request.target_apy,
            request.max_drawdown,
            user_prompt,
        )

        # Run with timeout
        try:
            result = await asyncio.wait_for(
                self._run_agent(system_prompt, user_prompt_text, context),
                timeout=self.settings.agent_timeout_seconds,
            )
            return result
        except asyncio.TimeoutError:
            return AgentResult(
                messages=[],
                success=False,
                error="Agent execution timed out",
            )
        except Exception as e:
            return AgentResult(
                messages=[],
                success=False,
                error=str(e),
            )

    async def run_followup(
        self,
        chat_id: str,
        chat_record: ChatRecord,
        user_prompt: str,
    ) -> AgentResult:
        """Run agent for followup message.

        Args:
            chat_id: Chat identifier
            chat_record: Existing chat record with history
            user_prompt: User's new message

        Returns:
            Agent result with messages and optional portfolio update
        """
        # Create tool context with existing portfolio
        context = ToolContext(
            chat_id=chat_id,
            backend_client=self.backend_client,
            chat_store=self.chat_store,
            current_portfolio=chat_record.portfolio,
        )

        # Format prompts
        system_prompt = format_system_prompt(
            chat_record.strategy,
            chat_record.target_apy,
            chat_record.max_drawdown,
        )

        chat_history = self._format_history(chat_record.messages, chat_record.portfolio)
        user_prompt_text = format_followup_prompt(chat_history, user_prompt)

        # Run with timeout
        try:
            result = await asyncio.wait_for(
                self._run_agent(system_prompt, user_prompt_text, context),
                timeout=self.settings.agent_timeout_seconds,
            )
            return result
        except asyncio.TimeoutError:
            return AgentResult(
                messages=[],
                success=False,
                error="Agent execution timed out",
            )
        except Exception as e:
            return AgentResult(
                messages=[],
                success=False,
                error=str(e),
            )

    async def _run_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        context: ToolContext,
    ) -> AgentResult:
        """Execute agent using Claude Agent SDK.

        Args:
            system_prompt: Formatted system prompt
            user_prompt: Formatted user prompt
            context: Tool context for state management

        Returns:
            Agent result with all outputs
        """
        # Create tools with shared context
        tools = PortfolioTools(context)

        # Create Agent with MCP server from tools
        agent = Agent(
            oauth_token=self.settings.claude_code_oauth_token,
            system_prompt=system_prompt,
            model="claude-sonnet-4-5-20250929",
            mcp_servers={"portfolio_advisor": tools.server},
        )

        # Run agent
        result_text = await agent.arun(user_prompt)

        # Compile final result
        final_message = result_text.strip() if result_text else "I've completed the analysis."

        agent_message = ChatMessage(
            type="agent",
            message=final_message,
            reasonings=context.reasonings,
        )

        return AgentResult(
            messages=[agent_message],
            portfolio=context.current_portfolio,
            success=True,
        )

    def _format_history(self, messages: list[ChatMessage], current_portfolio: Optional[dict] = None) -> str:
        """Format chat history for prompt with complete context.

        Args:
            messages: List of chat messages
            current_portfolio: Current portfolio state (optional)

        Returns:
            Formatted history string with messages, tool calls, reasoning, and portfolio state
        """
        lines = []
        for msg in messages:
            if msg.type == "user":
                lines.append(f"User: {msg.message}")
            elif msg.type == "system":
                lines.append(f"System: {msg.message}")
            else:  # agent message
                lines.append(f"Assistant: {msg.message}")

                # Include tool calls with key insights
                if msg.toolcalls:
                    tool_summaries = []
                    for toolcall in msg.toolcalls:
                        if isinstance(toolcall, dict):
                            formatted_tool = self._format_toolcall(toolcall)
                            if formatted_tool:
                                tool_summaries.append(formatted_tool)

                    if tool_summaries:
                        lines.append("\n  Tools used:")
                        for summary in tool_summaries:
                            lines.append(f"  {summary}")

                # Include detailed reasoning (not just summaries)
                if msg.reasonings:
                    reasoning_details = []
                    for reasoning in msg.reasonings:
                        if isinstance(reasoning, dict):
                            formatted_reasoning = self._format_reasoning(reasoning)
                            if formatted_reasoning:
                                reasoning_details.append(formatted_reasoning)

                    if reasoning_details:
                        lines.append("\n  Reasoning:")
                        for detail in reasoning_details:
                            lines.append(f"  {detail}")

        # Add current portfolio state at the end if available
        if current_portfolio:
            lines.append("\n" + "="*60)
            lines.append("CURRENT PORTFOLIO STATE:")
            lines.append("="*60)

            positions = current_portfolio.get("positions", [])
            if positions:
                lines.append(f"\nPortfolio has {len(positions)} position(s):")
                for i, pos in enumerate(positions, 1):
                    asset = pos.get("asset", "Unknown")
                    position_type = pos.get("position_type", "unknown")
                    quantity = pos.get("quantity", 0)
                    leverage = pos.get("leverage", 1.0)
                    entry_price = pos.get("entry_price")

                    pos_line = f"  {i}. {asset} - {position_type}, qty: {quantity}"
                    if leverage and leverage != 1.0:
                        pos_line += f", leverage: {leverage}x"
                    if entry_price:
                        pos_line += f", entry: ${entry_price:,.2f}"
                    lines.append(pos_line)

                # Add explanation if present
                explanation = current_portfolio.get("explanation", "")
                if explanation:
                    lines.append(f"\nPortfolio explanation: {explanation[:200]}...")
            else:
                lines.append("\nNo portfolio has been set yet.")

        return "\n\n".join(lines)

    def _format_toolcall(self, toolcall: dict) -> Optional[str]:
        """Format a tool call with key insights.

        Args:
            toolcall: Tool call dictionary with tool_name, inputs, outputs, status

        Returns:
            Formatted tool call summary or None if not formattable
        """
        tool_name = toolcall.get("tool_name", "")
        inputs = toolcall.get("inputs", {})
        outputs = toolcall.get("outputs", {})
        status = toolcall.get("status", "unknown")

        if status == "error":
            error_msg = outputs.get("error", "Unknown error")
            return f"- [{tool_name}] ERROR: {error_msg}"

        # Format based on tool type
        if tool_name == "get_aggregated_stats":
            assets = inputs.get("assets", [])
            if isinstance(assets, str):
                assets = [assets]

            # Extract key metrics from outputs
            stats_data = outputs.get("data", {})
            asset_stats = []
            for asset in assets:
                if asset in stats_data:
                    asset_data = stats_data[asset]
                    spot = asset_data.get("spot", {})
                    if spot:
                        volatility = spot.get("volatility", 0)
                        sharpe = spot.get("sharpe_ratio", 0)
                        max_dd = spot.get("max_drawdown", 0)
                        asset_stats.append(
                            f"{asset} (vol: {volatility:.1%}, sharpe: {sharpe:.2f}, max_dd: {max_dd:.1%})"
                        )

            if asset_stats:
                return f"- [get_aggregated_stats] Analyzed {', '.join(asset_stats)}"
            else:
                return f"- [get_aggregated_stats] Fetched data for {', '.join(assets)}"

        elif tool_name == "calculate_risk_profile":
            # Extract key risk metrics
            risk_data = outputs.get("data", {})
            metrics = risk_data.get("metrics", {})

            if metrics:
                var_95 = metrics.get("var_95", 0)
                max_dd = metrics.get("max_drawdown", 0)
                sharpe = metrics.get("sharpe_ratio", 0)
                total_value = metrics.get("total_value_usd", 0)

                metric_parts = [
                    f"value: ${total_value:,.0f}",
                    f"VaR(95%): {var_95:.1%}",
                    f"max_dd: {max_dd:.1%}",
                    f"sharpe: {sharpe:.2f}"
                ]

                # Add lending metrics if present
                lending = risk_data.get("lending_metrics")
                if lending:
                    ltv = lending.get("ltv_ratio", 0)
                    health = lending.get("health_factor", 0)
                    metric_parts.extend([
                        f"LTV: {ltv:.1%}",
                        f"health: {health:.2f}"
                    ])

                return f"- [calculate_risk_profile] {', '.join(metric_parts)}"
            else:
                return f"- [calculate_risk_profile] Computed risk metrics"

        else:
            # Generic format for other tools
            return f"- [{tool_name}] Executed successfully"

    def _format_reasoning(self, reasoning: dict) -> Optional[str]:
        """Format a reasoning step with summary and detail.

        Args:
            reasoning: Reasoning dictionary with summary, detail, timestamp

        Returns:
            Formatted reasoning or None if not formattable
        """
        summary = reasoning.get("summary", "").strip()
        detail = reasoning.get("detail", "").strip()

        if not summary:
            return None

        # If detail exists and adds value, include it
        if detail and detail != summary:
            # Limit detail to reasonable length (first 300 chars)
            if len(detail) > 300:
                detail = detail[:297] + "..."
            return f"- {summary}\n    → {detail}"
        else:
            return f"- {summary}"

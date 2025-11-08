"""Reasoning step tool for transparent decision tracking."""

from typing import Annotated, Any, Dict

from src.agent.models import ToolContext
from src.wrapper import BaseTool, tool


class ReasoningTools(BaseTool):
    """Tools for recording reasoning and decision-making processes."""

    tool_server_name = "portfolio_advisor_reasoning"
    tool_server_version = "1.0.0"

    def __init__(self, context: ToolContext) -> None:
        """Initialize reasoning tools with shared context.

        Args:
            context: Tool context with chat_id, backend_client, and portfolio state
        """
        self.context = context
        super().__init__()

    @tool()
    async def reasoning_step(
        self,
        brief_summary: Annotated[
            str,
            "Brief 1-2 sentence summary of this reasoning step (e.g., 'Phase 1 complete: Identified conservative investor profile')",
        ],
        reasoning_detail: Annotated[
            str,
            "Detailed explanation of the reasoning, analysis, data insights, trade-offs considered, and decisions made in this step.",
        ],
    ) -> Dict[str, Any]:
        """Record a reasoning step to provide transparency in decision-making.

        Use this tool to document your thought process throughout the portfolio
        advisory workflow. This helps users understand WHY you made certain decisions
        and builds trust through transparency.

        **When to call this tool:**
        - MANDATORY: After completing each PHASE (1-6) in the workflow
        - OPTIONAL: When making important decisions (asset selection, risk trade-offs)
        - OPTIONAL: When interpreting complex data or comparing alternatives
        - OPTIONAL: When explaining educational concepts to the user

        The reasoning will be stored and made available to the user via the API,
        allowing them to see your complete decision-making process.
        """
        # Validate inputs
        if not brief_summary or not brief_summary.strip():
            return {
                "success": False,
                "error": "brief_summary is required and must not be empty",
                "hint": "Provide a short 1-2 sentence summary of this reasoning step."
            }

        if not reasoning_detail or not reasoning_detail.strip():
            return {
                "success": False,
                "error": "reasoning_detail is required and must not be empty",
                "hint": "Provide detailed explanation of your reasoning, analysis, and decisions."
            }

        # Format the reasoning entry
        reasoning_entry = f"{brief_summary}\n\n{reasoning_detail}"

        # Store in context (for agent's internal use)
        self.context.reasonings.append(reasoning_entry)

        # Write to Redis IMMEDIATELY for real-time visibility
        try:
            self.context.chat_store.append_reasoning(
                chat_id=self.context.chat_id,
                reasoning=reasoning_entry
            )
        except Exception as e:
            # Log error but don't fail the tool call
            import logging
            logging.getLogger(__name__).error(
                f"Failed to write reasoning to Redis: {e}"
            )

        return {
            "success": True,
            "message": "Reasoning step recorded successfully (visible in real-time via GET API)",
            "brief_summary": brief_summary,
            "total_reasoning_steps": len(self.context.reasonings),
        }

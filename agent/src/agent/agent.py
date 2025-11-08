"""Chat agent implementation using Claude Agent SDK."""

import asyncio
from typing import Optional

from src.agent.models import AgentResult, ToolContext
from src.agent.prompt import (
    format_followup_prompt,
    format_initial_prompt,
    format_system_prompt,
)
from src.agent.tools.base import PortfolioTools
from src.backend_client import BackendClient
from src.config import Settings
from src.models import ChatCreateRequest, ChatMessage, ChatRecord
from src.wrapper import Agent


class ChatAgent:
    """AI agent for portfolio risk advisory using Claude Agent SDK."""

    def __init__(self, settings: Settings, backend_client: BackendClient):
        """Initialize chat agent.

        Args:
            settings: Application settings
            backend_client: Backend API client
        """
        self.settings = settings
        self.backend_client = backend_client

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
            current_portfolio=chat_record.portfolio,
        )

        # Format prompts
        system_prompt = format_system_prompt(
            chat_record.strategy,
            chat_record.target_apy,
            chat_record.max_drawdown,
        )

        chat_history = self._format_history(chat_record.messages)
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

    def _format_history(self, messages: list[ChatMessage]) -> str:
        """Format chat history for prompt.

        Args:
            messages: List of chat messages

        Returns:
            Formatted history string
        """
        lines = []
        for msg in messages:
            if msg.type == "user":
                lines.append(f"User: {msg.message}")
            else:
                lines.append(f"Assistant: {msg.message}")
                if msg.reasonings:
                    lines.append(f"  (Reasoning: {'; '.join(msg.reasonings)})")

        return "\n\n".join(lines)

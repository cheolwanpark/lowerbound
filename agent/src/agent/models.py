"""Agent-specific models."""

from typing import Optional

from pydantic import BaseModel, Field

from src.backend_client import BackendClient
from src.models import ChatMessage, PortfolioPosition

# Forward reference to avoid circular import
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.storage.chat_store import ChatStore


class AgentResult(BaseModel):
    """Complete result from agent execution."""

    messages: list[ChatMessage] = Field(default_factory=list)
    portfolio: Optional[list[PortfolioPosition]] = None
    success: bool
    error: Optional[str] = None


class ToolContext:
    """Shared context passed to all tools during agent execution."""

    def __init__(
        self,
        chat_id: str,
        backend_client: BackendClient,
        chat_store: "ChatStore",
        current_portfolio: Optional[list[PortfolioPosition]] = None,
    ):
        """Initialize tool context.

        Args:
            chat_id: Current chat identifier
            backend_client: Backend API client
            chat_store: ChatStore for direct Redis writes
            current_portfolio: Existing portfolio positions (if any)
        """
        self.chat_id = chat_id
        self.backend_client = backend_client
        self.chat_store = chat_store
        self.current_portfolio = current_portfolio
        self.reasonings: list[str] = []

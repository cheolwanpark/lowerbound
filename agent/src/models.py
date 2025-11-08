"""Core Pydantic models for the agent API."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatCreateRequest(BaseModel):
    """Request model for creating a new chat."""

    user_prompt: str = Field(min_length=1, max_length=5000)
    strategy: Literal["Passive", "Conservative", "Aggressive"]
    target_apy: float = Field(ge=0, le=200)
    max_drawdown: float = Field(ge=0, le=100)


class FollowupRequest(BaseModel):
    """Request model for followup messages."""

    prompt: str = Field(min_length=1, max_length=5000)


class PortfolioPosition(BaseModel):
    """Individual position in a portfolio."""

    asset: str
    quantity: float = Field(gt=0)
    position_type: Literal[
        "spot",
        "futures_long",
        "futures_short",
        "lending_supply",
        "lending_borrow"
    ]
    entry_price: float = Field(ge=0)
    leverage: float = Field(ge=1, le=125, default=1.0)

    # Lending-specific fields
    entry_timestamp: Optional[datetime] = None
    entry_index: Optional[str] = None
    borrow_type: Optional[Literal["variable", "stable"]] = None


class ChatMessage(BaseModel):
    """Individual message in a chat conversation."""

    type: Literal["user", "agent"]
    message: str
    reasonings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRecord(BaseModel):
    """Complete chat record with history and portfolio."""

    id: str
    status: Literal["queued", "processing", "completed", "failed", "timeout"]
    strategy: str
    target_apy: float
    max_drawdown: float
    messages: list[ChatMessage] = Field(default_factory=list)
    portfolio: Optional[list[PortfolioPosition]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

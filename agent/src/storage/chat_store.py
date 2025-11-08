"""Chat storage using Redis with atomic operations."""

from datetime import datetime
from typing import Literal, Optional

import redis

from src.models import (
    ChatCreateRequest,
    ChatMessage,
    ChatRecord,
    PortfolioPosition,
    PortfolioVersion,
)


class ChatStore:
    """Store and retrieve chat records from Redis with atomic commits."""

    INDEX_KEY = "chats:index"
    KEY_PREFIX = "chat:record:"
    TTL_SECONDS = 7 * 24 * 3600  # 7 days

    def __init__(self, redis_client: redis.Redis):
        """Initialize chat store.

        Args:
            redis_client: Configured Redis client
        """
        self.redis = redis_client

    def create_chat(self, chat_id: str, request: ChatCreateRequest) -> ChatRecord:
        """Create a new chat in queued status.

        Args:
            chat_id: Unique chat identifier
            request: Chat creation request

        Returns:
            Created chat record
        """
        record = ChatRecord(
            id=chat_id,
            status="queued",
            strategy=request.strategy,
            target_apy=request.target_apy,
            max_drawdown=request.max_drawdown,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self._write_record(record)
        return record

    def commit_agent_result(
        self,
        chat_id: str,
        agent_messages: list[ChatMessage],
        portfolio: Optional[list[PortfolioPosition]],
        status: Literal["completed", "failed", "timeout"],
        error_message: Optional[str] = None,
    ) -> ChatRecord:
        """ATOMIC commit of all agent outputs in single transaction.

        Args:
            chat_id: Chat identifier
            agent_messages: Messages to append from agent
            portfolio: Updated portfolio positions (or None)
            status: Final status
            error_message: Optional error message

        Returns:
            Updated chat record
        """
        record = self._get_record(chat_id)
        record.messages.extend(agent_messages)
        if portfolio is not None:
            record.portfolio = portfolio
        record.status = status
        record.error_message = error_message
        record.updated_at = datetime.utcnow()
        self._write_record(record)
        return record

    def add_user_message(self, chat_id: str, message: str) -> ChatRecord:
        """Add user message and mark as queued for processing.

        Args:
            chat_id: Chat identifier
            message: User message text

        Returns:
            Updated chat record
        """
        record = self._get_record(chat_id)
        record.messages.append(
            ChatMessage(type="user", message=message, timestamp=datetime.utcnow())
        )
        record.status = "queued"
        record.updated_at = datetime.utcnow()
        self._write_record(record)
        return record

    def mark_processing(self, chat_id: str) -> ChatRecord:
        """Mark chat as processing.

        Args:
            chat_id: Chat identifier

        Returns:
            Updated chat record
        """
        record = self._get_record(chat_id)
        record.status = "processing"
        record.updated_at = datetime.utcnow()
        self._write_record(record)
        return record

    def append_reasoning(self, chat_id: str, reasoning: str) -> ChatRecord:
        """Append reasoning to the latest agent message (real-time streaming).

        Creates a placeholder agent message if none exists yet.

        Args:
            chat_id: Chat identifier
            reasoning: Reasoning text to append

        Returns:
            Updated chat record
        """
        record = self._get_record(chat_id)

        # Find latest agent message or create placeholder
        if record.messages and record.messages[-1].type == "agent":
            # Append to existing agent message
            record.messages[-1].reasonings.append(reasoning)
        else:
            # Create new placeholder agent message
            record.messages.append(
                ChatMessage(
                    type="agent",
                    message="[Agent is thinking...]",
                    reasonings=[reasoning],
                    timestamp=datetime.utcnow(),
                )
            )

        record.updated_at = datetime.utcnow()
        self._write_record(record)
        return record

    def add_portfolio_version(
        self,
        chat_id: str,
        portfolio: list[PortfolioPosition],
        explanation: str,
    ) -> ChatRecord:
        """Add a new portfolio version (real-time streaming).

        Creates a new version each time set_portfolio is called during agent execution.

        Args:
            chat_id: Chat identifier
            portfolio: Portfolio positions
            explanation: Explanation for this portfolio version

        Returns:
            Updated chat record
        """
        record = self._get_record(chat_id)

        # Calculate next version number
        next_version = len(record.portfolio_versions) + 1

        # Create new portfolio version
        new_version = PortfolioVersion(
            version=next_version,
            positions=portfolio,
            explanation=explanation,
            timestamp=datetime.utcnow(),
        )

        # Add to versions list
        record.portfolio_versions.append(new_version)

        # Also update the latest portfolio (backward compatibility)
        record.portfolio = portfolio

        record.updated_at = datetime.utcnow()
        self._write_record(record)
        return record

    def get_chat(self, chat_id: str) -> Optional[ChatRecord]:
        """Get chat record by ID.

        Args:
            chat_id: Chat identifier

        Returns:
            Chat record or None if not found
        """
        key = f"{self.KEY_PREFIX}{chat_id}"
        data = self.redis.get(key)
        if data is None:
            return None
        return ChatRecord.model_validate_json(data)

    def list_chats(self, limit: int = 50, offset: int = 0) -> list[ChatRecord]:
        """List chats with pagination (newest first).

        Args:
            limit: Maximum number of chats to return
            offset: Offset for pagination

        Returns:
            List of chat records
        """
        # Get chat IDs from sorted set (descending by timestamp)
        chat_ids = self.redis.zrevrange(
            self.INDEX_KEY,
            offset,
            offset + limit - 1
        )

        # Fetch records
        records = []
        for chat_id in chat_ids:
            record = self.get_chat(chat_id)
            if record:
                records.append(record)

        return records

    def _get_record(self, chat_id: str) -> ChatRecord:
        """Get chat record or raise error if not found.

        Args:
            chat_id: Chat identifier

        Returns:
            Chat record

        Raises:
            ValueError: If chat not found
        """
        record = self.get_chat(chat_id)
        if record is None:
            raise ValueError(f"Chat {chat_id} not found")
        return record

    def _write_record(self, record: ChatRecord) -> None:
        """Atomic write with TTL and index update.

        Args:
            record: Chat record to write
        """
        key = f"{self.KEY_PREFIX}{record.id}"
        payload = record.model_dump_json()

        # Use pipeline for atomic multi-operation
        pipe = self.redis.pipeline()
        pipe.set(key, payload)
        pipe.expire(key, self.TTL_SECONDS)
        pipe.zadd(self.INDEX_KEY, {record.id: record.created_at.timestamp()})
        pipe.execute()

"""Service layer for business logic."""

import time
import uuid

from rq import Queue

from src.models import ChatCreateRequest, ChatRecord, ChatSummary, FollowupRequest
from src.queue.worker import process_chat_request
from src.storage.chat_store import ChatStore


def create_chat_service(
    request: ChatCreateRequest,
    queue: Queue,
    chat_store: ChatStore,
) -> ChatRecord:
    """Create a new chat and enqueue agent processing.

    Args:
        request: Chat creation request
        queue: RQ queue
        chat_store: Chat storage

    Returns:
        Created chat record
    """
    # Generate chat ID
    chat_id = uuid.uuid4().hex

    # Create chat record in queued status
    record = chat_store.create_chat(chat_id, request)

    # Add initial user message
    chat_store.add_user_message(chat_id, request.user_prompt)

    # Enqueue background job
    queue.enqueue(
        process_chat_request,
        kwargs={
            "chat_id": chat_id,
            "is_followup": False,
            "user_prompt": request.user_prompt,
        },
        job_id=chat_id,
    )

    return record


def list_chats_service(
    chat_store: ChatStore,
    limit: int = 50,
    offset: int = 0,
) -> list[ChatSummary]:
    """List chats with pagination (concise summaries only).

    Args:
        chat_store: Chat storage
        limit: Maximum number of chats to return
        offset: Offset for pagination

    Returns:
        List of concise chat summaries
    """
    records = chat_store.list_chats(limit=limit, offset=offset)

    # Convert to concise summaries
    summaries = []
    for record in records:
        summaries.append(
            ChatSummary(
                id=record.id,
                status=record.status,
                strategy=record.strategy,
                target_apy=record.target_apy,
                max_drawdown=record.max_drawdown,
                title=record.title,
                has_portfolio=record.portfolio is not None,
                message_count=len(record.messages),
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        )

    return summaries


def get_chat_service(
    chat_id: str,
    chat_store: ChatStore,
) -> ChatRecord:
    """Get a chat by ID.

    Args:
        chat_id: Chat identifier
        chat_store: Chat storage

    Returns:
        Chat record

    Raises:
        ValueError: If chat not found
    """
    record = chat_store.get_chat(chat_id)
    if record is None:
        raise ValueError(f"Chat {chat_id} not found")
    return record


def get_portfolio_service(
    chat_id: str,
    chat_store: ChatStore,
) -> dict:
    """Get portfolio for a chat.

    Args:
        chat_id: Chat identifier
        chat_store: Chat storage

    Returns:
        Portfolio dict with all versions (DESC by timestamp, latest first)

    Raises:
        ValueError: If chat not found
    """
    record = get_chat_service(chat_id, chat_store)

    # Sort portfolio versions by timestamp (latest first)
    sorted_versions = sorted(
        record.portfolio_versions,
        key=lambda v: v.timestamp,
        reverse=True
    )

    return {
        "chat_id": chat_id,
        "portfolio_versions": [v.model_dump() for v in sorted_versions],
        "latest_portfolio": record.portfolio,
        "has_portfolio": record.portfolio is not None,
    }


def followup_service(
    chat_id: str,
    request: FollowupRequest,
    queue: Queue,
    chat_store: ChatStore,
) -> ChatRecord:
    """Add a followup message and enqueue processing.

    Args:
        chat_id: Chat identifier
        request: Followup request
        queue: RQ queue
        chat_store: Chat storage

    Returns:
        Updated chat record

    Raises:
        ValueError: If chat not found
    """
    # Verify chat exists
    get_chat_service(chat_id, chat_store)

    # Update parameters if provided
    if request.strategy or request.target_apy is not None or request.max_drawdown is not None:
        record, changes = chat_store.update_parameters(
            chat_id=chat_id,
            strategy=request.strategy,
            target_apy=request.target_apy,
            max_drawdown=request.max_drawdown,
        )

        # Add system message documenting parameter changes
        if changes:
            change_parts = []
            if "strategy" in changes:
                old, new = changes["strategy"]
                change_parts.append(f"Strategy: {old} → {new}")
            if "target_apy" in changes:
                old, new = changes["target_apy"]
                change_parts.append(f"Target APY: {old}% → {new}%")
            if "max_drawdown" in changes:
                old, new = changes["max_drawdown"]
                change_parts.append(f"Max Drawdown: {old}% → {new}%")

            system_msg = "Portfolio configuration updated: " + ", ".join(change_parts)
            chat_store.add_system_message(chat_id, system_msg)

    # Add user message
    record = chat_store.add_user_message(chat_id, request.prompt)

    # Enqueue job with unique ID
    job_id = f"{chat_id}_followup_{int(time.time() * 1000)}"
    queue.enqueue(
        process_chat_request,
        kwargs={
            "chat_id": chat_id,
            "is_followup": True,
            "user_prompt": request.prompt,
        },
        job_id=job_id,
    )

    return record

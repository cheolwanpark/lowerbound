"""API routes for the agent service."""

from fastapi import APIRouter, Depends, HTTPException, Request
from rq import Queue

from src.api.service import (
    create_chat_service,
    followup_service,
    get_chat_service,
    get_portfolio_service,
    list_chats_service,
)
from src.models import ChatCreateRequest, ChatRecord, FollowupRequest
from src.queue.queue import QueueConfig, create_queue
from src.storage.chat_store import ChatStore
from src.storage.redis_client import create_redis_client
from src.config import Settings

router = APIRouter()


# Dependency injection


def get_settings(request: Request) -> Settings:
    """Get settings from app state.

    Args:
        request: FastAPI request

    Returns:
        Application settings

    Raises:
        RuntimeError: If settings not initialized
    """
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("Settings not initialized in app state")
    return settings


def get_chat_store(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ChatStore:
    """Get or create ChatStore singleton.

    Args:
        request: FastAPI request
        settings: Application settings

    Returns:
        ChatStore instance
    """
    chat_store = getattr(request.app.state, "chat_store", None)
    if chat_store is None:
        redis_client = create_redis_client(settings)
        chat_store = ChatStore(redis_client)
        request.app.state.chat_store = chat_store
    return chat_store


def get_queue(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Queue:
    """Get or create RQ Queue singleton.

    Args:
        request: FastAPI request
        settings: Application settings

    Returns:
        RQ Queue instance
    """
    queue = getattr(request.app.state, "queue", None)
    if queue is None:
        redis_client = create_redis_client(settings)
        queue_config = QueueConfig(
            redis_url=settings.redis_url,
            queue_name=settings.queue_name,
        )
        queue = create_queue(queue_config, redis_client)
        request.app.state.queue = queue
    return queue


# Routes


@router.post("/chat", status_code=202, response_model=ChatRecord)
async def create_chat(
    request: ChatCreateRequest,
    queue: Queue = Depends(get_queue),
    chat_store: ChatStore = Depends(get_chat_store),
) -> ChatRecord:
    """Create a new chat and start agent processing in background.

    The chat is created immediately in 'queued' status and a background job
    is enqueued. Use GET /chat/{id} to poll for updates.

    Args:
        request: Chat creation request
        queue: RQ queue (injected)
        chat_store: Chat storage (injected)

    Returns:
        Created chat record with 'queued' status
    """
    return create_chat_service(request, queue, chat_store)


@router.get("/chat", response_model=list[ChatRecord])
async def list_chats(
    limit: int = 50,
    offset: int = 0,
    chat_store: ChatStore = Depends(get_chat_store),
) -> list[ChatRecord]:
    """List all chats with pagination (newest first).

    Args:
        limit: Maximum number of chats to return (default: 50)
        offset: Offset for pagination (default: 0)
        chat_store: Chat storage (injected)

    Returns:
        List of chat records
    """
    if limit < 1 or limit > 100:
        raise HTTPException(400, "limit must be between 1 and 100")

    if offset < 0:
        raise HTTPException(400, "offset must be >= 0")

    return list_chats_service(chat_store, limit, offset)


@router.get("/chat/{chat_id}", response_model=ChatRecord)
async def get_chat(
    chat_id: str,
    chat_store: ChatStore = Depends(get_chat_store),
) -> ChatRecord:
    """Get a chat by ID with full message history.

    Args:
        chat_id: Chat identifier
        chat_store: Chat storage (injected)

    Returns:
        Chat record with all messages

    Raises:
        HTTPException: 404 if chat not found
    """
    try:
        return get_chat_service(chat_id, chat_store)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/chat/{chat_id}/portfolio")
async def get_portfolio(
    chat_id: str,
    chat_store: ChatStore = Depends(get_chat_store),
) -> dict:
    """Get the current portfolio for a chat.

    Args:
        chat_id: Chat identifier
        chat_store: Chat storage (injected)

    Returns:
        Portfolio dict with positions

    Raises:
        HTTPException: 404 if chat not found
    """
    try:
        return get_portfolio_service(chat_id, chat_store)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/chat/{chat_id}/followup", status_code=202, response_model=ChatRecord)
async def add_followup(
    chat_id: str,
    request: FollowupRequest,
    queue: Queue = Depends(get_queue),
    chat_store: ChatStore = Depends(get_chat_store),
) -> ChatRecord:
    """Add a followup message to continue the conversation.

    The message is added immediately and a background job is enqueued.
    Use GET /chat/{id} to poll for the agent's response.

    Args:
        chat_id: Chat identifier
        request: Followup request with prompt
        queue: RQ queue (injected)
        chat_store: Chat storage (injected)

    Returns:
        Updated chat record with 'queued' status

    Raises:
        HTTPException: 404 if chat not found
    """
    try:
        return followup_service(chat_id, request, queue, chat_store)
    except ValueError as e:
        raise HTTPException(404, str(e))

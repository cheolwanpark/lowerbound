"""Background worker function for processing chat requests."""

import asyncio
import logging

import httpx

from src.agent.agent import ChatAgent
from src.backend_client import BackendClient
from src.config import Settings
from src.models import ChatCreateRequest
from src.storage.chat_store import ChatStore
from src.storage.redis_client import create_redis_client

logger = logging.getLogger(__name__)


def process_chat_request(
    *,
    chat_id: str,
    is_followup: bool = False,
    user_prompt: str = "",
) -> dict:
    """Background worker: run agent and atomically commit results to Redis.

    This function is executed by RQ workers in the background. It loads
    the necessary dependencies, runs the AI agent, and commits all results
    atomically to Redis.

    Args:
        chat_id: Chat identifier
        is_followup: Whether this is a followup message
        user_prompt: User's message/prompt

    Returns:
        dict with job result

    Raises:
        Exception: If agent execution fails (will be logged by RQ)
    """
    # Load settings
    settings = Settings.from_env()
    settings.validate()

    # Create Redis client and storage
    redis_client = create_redis_client(settings)
    chat_store = ChatStore(redis_client)

    # Create HTTP client for backend
    httpx_client = httpx.AsyncClient()
    backend_client = BackendClient(settings.backend_api_url, httpx_client)

    try:
        # Mark as processing
        chat_store.mark_processing(chat_id)

        # Create agent
        agent = ChatAgent(settings, backend_client)

        # Run agent based on request type
        if is_followup:
            chat_record = chat_store.get_chat(chat_id)
            if not chat_record:
                raise ValueError(f"Chat {chat_id} not found")

            result = asyncio.run(
                agent.run_followup(chat_id, chat_record, user_prompt)
            )
        else:
            # Initial chat
            chat_record = chat_store.get_chat(chat_id)
            if not chat_record:
                raise ValueError(f"Chat {chat_id} not found")

            request = ChatCreateRequest(
                user_prompt=user_prompt,
                strategy=chat_record.strategy,
                target_apy=chat_record.target_apy,
                max_drawdown=chat_record.max_drawdown,
            )

            result = asyncio.run(
                agent.run_initial(chat_id, request, user_prompt)
            )

        # ATOMIC commit: write all agent outputs in single transaction
        if result.success:
            chat_store.commit_agent_result(
                chat_id=chat_id,
                agent_messages=result.messages,
                portfolio=result.portfolio,
                status="completed",
            )
            logger.info(f"Chat {chat_id} completed successfully")
        else:
            chat_store.commit_agent_result(
                chat_id=chat_id,
                agent_messages=[],
                portfolio=None,
                status="failed",
                error_message=result.error,
            )
            logger.error(f"Chat {chat_id} failed: {result.error}")

        return {
            "chat_id": chat_id,
            "success": result.success,
            "error": result.error,
        }

    except Exception as exc:
        # Log error and mark as failed
        logger.exception(f"Worker error for chat {chat_id}")

        try:
            chat_store.commit_agent_result(
                chat_id=chat_id,
                agent_messages=[],
                portfolio=None,
                status="failed",
                error_message=str(exc),
            )
        except Exception as commit_error:
            logger.exception(f"Failed to commit error state for chat {chat_id}: {commit_error}")

        raise

    finally:
        # Clean up HTTP client
        asyncio.run(httpx_client.aclose())

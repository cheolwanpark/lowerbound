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
    backend_client = BackendClient(
        settings.backend_api_url,
        httpx_client,
        api_key=settings.backend_api_key if settings.backend_api_key else None,
    )

    try:
        # Mark as processing
        chat_store.mark_processing(chat_id)

        # Create agent
        agent = ChatAgent(settings, backend_client, chat_store)

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

        # FINAL commit: merge in-memory results with real-time Redis writes
        # Note: Tools (reasoning_step, set_portfolio) already wrote to Redis during execution.
        # This commit ensures final status is set and any remaining data is persisted.
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
        error_type = type(exc).__name__
        logger.exception(f"Worker error for chat {chat_id}: {error_type}")

        # Create user-friendly error message
        if "validation error" in str(exc).lower() or "ValidationError" in error_type:
            error_msg = f"Data validation error: {str(exc)[:500]}"
        elif "timeout" in str(exc).lower():
            error_msg = "Request timeout - the operation took too long"
        else:
            error_msg = f"{error_type}: {str(exc)[:500]}"

        try:
            chat_store.commit_agent_result(
                chat_id=chat_id,
                agent_messages=[],
                portfolio=None,
                status="failed",
                error_message=error_msg,
            )
        except Exception as commit_error:
            logger.exception(f"Failed to commit error state for chat {chat_id}: {commit_error}")
            # Try one more time with minimal error info
            try:
                chat_store.commit_agent_result(
                    chat_id=chat_id,
                    agent_messages=[],
                    portfolio=None,
                    status="failed",
                    error_message=f"Fatal error: {error_type}",
                )
            except Exception:
                logger.error(f"Unable to save error state for chat {chat_id}")

        raise

    finally:
        # Clean up HTTP client gracefully
        try:
            # Try to get the current event loop
            try:
                loop = asyncio.get_running_loop()
                # Loop is running - we can't close client synchronously
                # Create a task to close it later
                loop.create_task(httpx_client.aclose())
                logger.debug("Scheduled httpx client cleanup on running loop")
            except RuntimeError:
                # No running loop - try to get or create one
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        # Loop is closed, create a new one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    # Run the cleanup
                    loop.run_until_complete(httpx_client.aclose())
                    logger.debug("Successfully closed httpx client")
                except Exception as loop_error:
                    logger.debug(f"Could not close httpx client via event loop: {loop_error}")
                    # Last resort: try to close synchronously (httpx supports this)
                    try:
                        # httpx AsyncClient has internal cleanup that can handle this
                        import gc
                        httpx_client = None
                        gc.collect()
                        logger.debug("Forced httpx client cleanup via garbage collection")
                    except Exception:
                        pass
        except Exception as cleanup_error:
            # Log but don't fail the job due to cleanup issues
            logger.debug(f"HTTP client cleanup warning: {cleanup_error}")

"""Queue configuration and factory for background job processing."""

from dataclasses import dataclass

import redis
from rq import Queue


@dataclass
class QueueConfig:
    """Configuration for the background worker queue."""

    redis_url: str
    queue_name: str
    default_timeout: int = 30 * 60  # 30 minutes


def create_queue(config: QueueConfig, connection: redis.Redis) -> Queue:
    """Create an RQ queue for background job processing.

    Args:
        config: Queue configuration
        connection: Redis connection

    Returns:
        Configured RQ queue
    """
    return Queue(
        name=config.queue_name,
        connection=connection,
        default_timeout=config.default_timeout,
    )

"""Redis client factory."""

import redis

from src.config import Settings


def create_redis_client(settings: Settings) -> redis.Redis:
    """Create a Redis client with proper configuration.

    Args:
        settings: Application settings

    Returns:
        Configured Redis client with string decoding
    """
    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )


import os

import redis
from django.conf import settings


def create_rate_limit_redis_client():
    """
    Create a dedicated Redis client for rate limiting.
    """

    redis_url = getattr(
        settings,
        "RATE_LIMIT_REDIS_URL",
        os.getenv("RATE_LIMIT_REDIS_URL")
    )

    if not redis_url:
        raise RuntimeError(
            "RATE_LIMIT_REDIS_URL is not configured."
        )

    pool = redis.ConnectionPool.from_url(
        redis_url,
        decode_responses=True,
        max_connections=50,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
    )

    return redis.Redis(connection_pool=pool)


# Shared client for the application process
redis_client = create_rate_limit_redis_client()

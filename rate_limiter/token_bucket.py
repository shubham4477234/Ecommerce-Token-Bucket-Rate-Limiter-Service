
import hashlib
import math
from dataclasses import dataclass

import redis

from .config import get_rate_limit_policy
from .lua_script import TOKEN_BUCKET_SCRIPT
from .redis_client import redis_client


class RateLimiterUnavailable(Exception):
    """Raised when the rate limiter cannot communicate with Redis."""


@dataclass(frozen=True)
class TokenBucketResult:
    allowed: bool
    remaining_tokens: float
    retry_after_seconds: int
    reset_after_seconds: int


class TokenBucketService:

    def __init__(self):

        # Register the Lua script with Redis
        self.script = redis_client.register_script(
            TOKEN_BUCKET_SCRIPT
        )

    @staticmethod
    def generate_key(scope, identifier):

        # Hash the identifier to avoid exposing user IDs or IPs in Redis keys
        identifier_hash = hashlib.sha256(
            identifier.encode("utf-8")
        ).hexdigest()

        return f"limitguard:{scope}:{identifier_hash}"

    def consume(self, scope, identifier, requested_tokens=1):

        # 1. Validate inputs
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError("A valid scope is required.")

        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("A valid client identifier is required.")

        if (
            isinstance(requested_tokens, bool)
            or not isinstance(requested_tokens, int)
            or requested_tokens <= 0
        ):
            raise ValueError(
                "Requested tokens must be a positive integer."
            )

        # 2. Get the policy
        policy = get_rate_limit_policy(scope)

        if requested_tokens > policy.capacity:
            raise ValueError(
                "Requested tokens cannot exceed bucket capacity."
            )

        # 3. Generate Redis key
        redis_key = self.generate_key(scope, identifier)

        # 4. Calculate expiry
        # Keep the key long enough for a completely empty bucket
        # to refill, plus an additional 60-second safety margin.
        ttl_seconds = max(
            60,
            math.ceil(policy.capacity / policy.refill_rate) + 60
        )

        # 5. Execute atomic Lua script
        try:

            result = self.script(
                keys=[redis_key],
                args=[
                    policy.capacity,
                    policy.refill_rate,
                    requested_tokens,
                    ttl_seconds
                ]
            )

        except redis.RedisError as exc:

            raise RateLimiterUnavailable(
                "Unable to communicate with Redis."
            ) from exc

        # 6. Parse Lua response
        allowed, remaining, retry_ms, reset_ms = result

        return TokenBucketResult(
            allowed=bool(int(allowed)),
            remaining_tokens=float(remaining),
            retry_after_seconds=math.ceil(int(retry_ms) / 1000),
            reset_after_seconds=math.ceil(int(reset_ms) / 1000)
        )


# Shared service instance
token_bucket_service = TokenBucketService()

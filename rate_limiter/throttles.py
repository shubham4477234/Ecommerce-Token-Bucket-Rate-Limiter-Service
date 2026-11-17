
from rest_framework.throttling import BaseThrottle
from django.core.exceptions import ImproperlyConfigured

from .identifiers import get_client_identifier
from .token_bucket import (
    token_bucket_service,
    RateLimiterUnavailable,
)
from .config import get_rate_limit_policy
from .exceptions import RateLimiterUnavailableAPIException


class TokenBucketThrottle(BaseThrottle):

    def __init__(self):

        self.retry_after = None
        self.rate_limit_info = None

    def allow_request(self, request, view):

        # 1. Identify the API scope
        scope = getattr(view, "throttle_scope", None)

        if not scope:
            raise ImproperlyConfigured(
                f"{view.__class__.__name__} must define throttle_scope."
            )

        # 2. Identify the client
        identifier = get_client_identifier(request)

        # 3. Get the API policy
        policy = get_rate_limit_policy(scope)

        # 4. Execute Token Bucket
        try:

            result = token_bucket_service.consume(
                scope=scope,
                identifier=identifier,
            )

        except RateLimiterUnavailable as exc:

            # Fail closed: do not bypass protection if Redis fails
            raise RateLimiterUnavailableAPIException() from exc

        # 5. Store rate-limit information for response headers later
        self.rate_limit_info = {
            "limit": policy.capacity,
            "remaining": max(
                0,
                int(result.remaining_tokens)
            ),
            "reset_after": result.reset_after_seconds,
        }

        # 6. If rejected, save retry information
        if not result.allowed:

            self.retry_after = result.retry_after_seconds

            return False

        return True

    def wait(self):

        return self.retry_after


from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitPolicy:
    """
    Configuration for a Token Bucket.
    """

    capacity: int
    refill_rate: float

    def __post_init__(self):

        if isinstance(self.capacity, bool) or not isinstance(self.capacity, int):
            raise ValueError("Capacity must be a positive integer.")

        if self.capacity <= 0:
            raise ValueError("Capacity must be greater than zero.")

        if isinstance(self.refill_rate, bool) or not isinstance(
            self.refill_rate, (int, float)
        ):
            raise ValueError("Refill rate must be a positive number.")

        if self.refill_rate <= 0:
            raise ValueError("Refill rate must be greater than zero.")


# Default policy for APIs without a specific configuration
DEFAULT_POLICY = RateLimitPolicy(
    capacity=10,
    refill_rate=1.0
)


# API-specific policies
RATE_LIMITS = {

    "login": RateLimitPolicy(
        capacity=5,
        refill_rate=0.1
    ),

    "register": RateLimitPolicy(
        capacity=3,
        refill_rate=0.05
    ),

    "products": RateLimitPolicy(
        capacity=10,
        refill_rate=1.0
    ),

    "product-details": RateLimitPolicy(
        capacity=15,
        refill_rate=1.0
    ),

    "cart": RateLimitPolicy(
        capacity=8,
        refill_rate=0.5
    ),

    "orders": RateLimitPolicy(
        capacity=3,
        refill_rate=0.1
    ),

    "addresses": RateLimitPolicy(
        capacity=5,
        refill_rate=0.2
    ),

}


def get_rate_limit_policy(scope: str) -> RateLimitPolicy:
    """
    Return the rate-limit policy for the requested API scope.
    """

    if not isinstance(scope, str) or not scope.strip():
        raise ValueError("A valid rate-limit scope is required.")

    return RATE_LIMITS.get(scope, DEFAULT_POLICY)

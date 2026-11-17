
import time


class TokenBucket:

    def __init__(self, capacity, refill_rate):

        self.capacity = capacity
        self.refill_rate = refill_rate

        # Initially, the bucket is full
        self.tokens = capacity

        # Store the initial timestamp
        self.last_refill_time = time.time()

    def refill(self):

        current_time = time.time()

        # Calculate elapsed time
        elapsed_time = current_time - self.last_refill_time

        # Calculate tokens to add
        tokens_to_add = elapsed_time * self.refill_rate

        # Refill bucket without exceeding capacity
        self.tokens = min(
            self.capacity,
            self.tokens + tokens_to_add
        )

        # Update timestamp
        self.last_refill_time = current_time

    def consume(self, tokens=1):

        # Refill before checking availability
        self.refill()

        if self.tokens >= tokens:

            self.tokens -= tokens

            return True

        return False

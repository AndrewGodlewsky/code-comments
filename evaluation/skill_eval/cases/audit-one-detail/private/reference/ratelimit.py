# SPDX-License-Identifier: Apache-2.0
import time

# Per-client defaults from the API contract: bursts of up to 20 requests,
# 5 requests per second sustained.
DEFAULT_CAPACITY = 20
DEFAULT_RATE = 5


class TokenBucket:
    """Allow bursts of up to ``capacity`` requests, refilled at ``rate`` tokens per second."""

    def __init__(self, capacity=DEFAULT_CAPACITY, rate=DEFAULT_RATE, clock=time.monotonic):
        self.capacity = capacity
        self.rate = rate
        self.clock = clock
        # Start full so a freshly deployed instance doesn't reject the load
        # balancer's first burst of health checks.
        self.tokens = capacity
        self.updated = clock()

    def _refill(self):
        now = self.clock()
        # Clamp at zero: monotonic clocks never go backwards, but tests inject
        # fake clocks that do, and a negative refill would drain the bucket.
        elapsed = max(0.0, now - self.updated)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.updated = now

    def try_acquire(self, cost=1):
        """Take ``cost`` tokens and return True if enough are available, else return False. Never blocks."""
        self._refill()
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False

    def wait_time(self, cost=1):
        """Seconds until ``cost`` tokens are available (0.0 if they already are)."""
        self._refill()
        return max(0.0, (cost - self.tokens) / self.rate)

"""Geocode addresses through Geoway.

The client sends at most 100 requests a minute and waits when it reaches that limit.
"""

import time

from geo.limits import REQUESTS_PER_MINUTE


class Throttle:
    """Space calls evenly so that no minute goes over the limit."""

    def __init__(self, per_minute=REQUESTS_PER_MINUTE, clock=time.monotonic, sleep=time.sleep):
        self.interval = 60.0 / per_minute
        self.clock = clock
        self.sleep = sleep
        self.next_at = 0.0

    def wait(self):
        """Block until the next call is allowed."""
        now = self.clock()
        if now < self.next_at:
            self.sleep(self.next_at - now)
            now = self.next_at
        self.next_at = now + self.interval

"""Group push notifications into provider calls.

Notifications are sent in batches of up to 100, so a busy minute costs a handful
of provider calls instead of thousands.
"""

import time

from notify.config import BATCH_SIZE, FLUSH_INTERVAL_S


class Batcher:
    """Collect notifications and hand full or stale batches to `send`."""

    def __init__(self, send, clock=time.monotonic):
        self.send = send
        self.clock = clock
        self.pending = []
        self.oldest = None

    def add(self, notification):
        if not self.pending:
            self.oldest = self.clock()
        self.pending.append(notification)
        if len(self.pending) >= BATCH_SIZE:
            self.flush()

    def tick(self):
        """Send a partial batch once its oldest notification has waited long enough."""
        if self.pending and self.clock() - self.oldest >= FLUSH_INTERVAL_S:
            self.flush()

    def flush(self):
        batch, self.pending, self.oldest = self.pending, [], None
        if batch:
            self.send(batch)

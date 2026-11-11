"""The fulfilment queue that the poller fills and the packing screen reads.

Orders are packed in the order they were queued. An order has already waited about 300 s
on average by the time it is queued, so the packing screen shows when the storefront
listed it, not when it was queued.
"""


class FulfilmentQueue(list):
    """Orders waiting to be packed, oldest queued first."""

    def next_order(self):
        """Remove and return the oldest queued order, or None if the queue is empty."""
        return self.pop(0) if self else None

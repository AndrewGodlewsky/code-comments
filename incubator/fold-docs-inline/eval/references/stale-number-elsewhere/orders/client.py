"""The shop API client used by the nightly sync."""

import time

from orders.backoff import pause_after
from orders.settings import ATTEMPTS

# Keep at 250 or below: the shop API answers a larger page size with HTTP 400 and
# returns no orders.
PAGE_SIZE = 200


class ShopClient:
    def __init__(self, http, sleep=time.sleep):
        self.http = http
        self.sleep = sleep

    def get_page(self, page):
        """Return one page of orders, or an empty list once every order has been read."""
        # The shop API drops about one request in a thousand during its nightly
        # maintenance (OPS-19), so a dropped request is tried again.
        for attempt in range(1, ATTEMPTS + 1):
            try:
                return self.http.get("/orders", page=page, page_size=PAGE_SIZE)
            except ConnectionError:
                if attempt == ATTEMPTS:
                    raise
                self.sleep(pause_after(attempt))

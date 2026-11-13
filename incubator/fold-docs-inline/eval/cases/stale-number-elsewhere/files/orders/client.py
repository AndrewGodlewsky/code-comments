"""The shop API client used by the nightly sync."""

import time

from orders.backoff import pause_after
from orders.settings import ATTEMPTS

PAGE_SIZE = 200


class ShopClient:
    def __init__(self, http, sleep=time.sleep):
        self.http = http
        self.sleep = sleep

    def get_page(self, page):
        """Return one page of orders, or an empty list once every order has been read."""
        for attempt in range(1, ATTEMPTS + 1):
            try:
                return self.http.get("/orders", page=page, page_size=PAGE_SIZE)
            except ConnectionError:
                if attempt == ATTEMPTS:
                    raise
                self.sleep(pause_after(attempt))

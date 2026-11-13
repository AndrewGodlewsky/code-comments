import unittest

from orders.client import PAGE_SIZE, ShopClient
from orders.settings import ATTEMPTS, PAUSE_SECONDS


class FlakyHttp:
    def __init__(self, failures, orders):
        self.failures = failures
        self.orders = orders
        self.calls = []

    def get(self, path, page, page_size):
        self.calls.append((path, page, page_size))
        if len(self.calls) <= self.failures:
            raise ConnectionError("dropped")
        return self.orders


class ShopClientTest(unittest.TestCase):
    def test_retries_a_dropped_request(self):
        pauses = []
        http = FlakyHttp(1, [{"id": "a"}])
        self.assertEqual(ShopClient(http, sleep=pauses.append).get_page(1), [{"id": "a"}])
        self.assertEqual(http.calls, [("/orders", 1, PAGE_SIZE)] * 2)
        self.assertEqual(pauses, [PAUSE_SECONDS])

    def test_gives_up_after_the_last_attempt(self):
        http = FlakyHttp(ATTEMPTS, [])
        with self.assertRaises(ConnectionError):
            ShopClient(http, sleep=lambda seconds: None).get_page(1)
        self.assertEqual(len(http.calls), ATTEMPTS)


if __name__ == "__main__":
    unittest.main()

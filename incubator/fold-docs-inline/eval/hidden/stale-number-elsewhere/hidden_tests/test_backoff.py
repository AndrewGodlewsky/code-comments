import unittest

from orders.client import ShopClient


class FlakyHttp:
    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def get(self, path, page, page_size):
        self.calls += 1
        if self.calls <= self.failures:
            raise ConnectionError("dropped")
        return [{"id": "a"}]


class BackoffTest(unittest.TestCase):
    def test_each_pause_doubles(self):
        pauses = []
        http = FlakyHttp(4)
        self.assertEqual(ShopClient(http, sleep=pauses.append).get_page(1), [{"id": "a"}])
        self.assertEqual(pauses, [2, 4, 8, 16])
        self.assertEqual(http.calls, 5)

    def test_the_fifth_drop_is_raised(self):
        http = FlakyHttp(5)
        with self.assertRaises(ConnectionError):
            ShopClient(http, sleep=lambda seconds: None).get_page(1)
        self.assertEqual(http.calls, 5)

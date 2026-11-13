import unittest
from datetime import datetime, timedelta

from orders.settings import ORDER_WINDOW_DAYS
from orders.store import OrderStore
from orders.sync import sync_orders

NOW = datetime(2026, 3, 1, 2, 15)


class FakeClient:
    def __init__(self, pages):
        self.pages = pages

    def get_page(self, page):
        return self.pages[page - 1] if page <= len(self.pages) else []


class SyncOrdersTest(unittest.TestCase):
    def test_writes_recent_orders_from_every_page(self):
        client = FakeClient([[{"id": "a", "placed_at": NOW}], [{"id": "b", "placed_at": NOW}]])
        store = OrderStore()
        self.assertEqual(sync_orders(client, store, NOW), 2)
        self.assertEqual(sorted(store.rows), ["a", "b"])

    def test_skips_orders_outside_the_window(self):
        old = NOW - timedelta(days=ORDER_WINDOW_DAYS + 1)
        client = FakeClient([[{"id": "old", "placed_at": old}, {"id": "new", "placed_at": NOW}]])
        store = OrderStore()
        sync_orders(client, store, NOW)
        self.assertEqual(list(store.rows), ["new"])


if __name__ == "__main__":
    unittest.main()

import unittest

from orders.poller import next_poll_at, run
from orders.queue import FulfilmentQueue
from orders.settings import POLL_INTERVAL_S


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Storefront:
    def __init__(self, pages):
        self.pages = list(pages)

    def new_orders(self, limit):
        return self.pages.pop(0)[:limit] if self.pages else []


class PollerTest(unittest.TestCase):
    def test_next_poll_is_one_interval_later(self):
        self.assertEqual(next_poll_at(1000), 1000 + POLL_INTERVAL_S)

    def test_each_order_is_queued_once(self):
        clock, queue = Clock(), FulfilmentQueue()
        store = Storefront([[{"id": 1}, {"id": 2}], [{"id": 2}, {"id": 3}]])
        run(store, queue, polls=2, clock=clock, sleep=clock.sleep)
        self.assertEqual([o["id"] for o in queue], [1, 2, 3])
        self.assertEqual(clock.now, POLL_INTERVAL_S)


class QueueTest(unittest.TestCase):
    def test_oldest_first(self):
        queue = FulfilmentQueue([{"id": 1}, {"id": 2}])
        self.assertEqual(queue.next_order(), {"id": 1})
        self.assertEqual(queue.next_order(), {"id": 2})
        self.assertIsNone(queue.next_order())


if __name__ == "__main__":
    unittest.main()

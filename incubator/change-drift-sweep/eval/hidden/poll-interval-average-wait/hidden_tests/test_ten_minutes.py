import unittest

from orders import settings
from orders.poller import next_poll_at, run


class Clock:
    def __init__(self):
        self.now = 0.0
        self.slept = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


class Empty:
    def new_orders(self, limit):
        return []


class TenMinutesTest(unittest.TestCase):
    def test_interval_is_600_seconds(self):
        self.assertEqual(settings.POLL_INTERVAL_S, 600)
        self.assertEqual(next_poll_at(1000), 1600)

    def test_run_waits_ten_minutes_between_polls(self):
        clock = Clock()
        run(Empty(), [], polls=3, clock=clock, sleep=clock.sleep)
        self.assertEqual(clock.slept, [600, 600])

    def test_page_limit_unchanged(self):
        self.assertEqual(settings.PAGE_LIMIT, 100)

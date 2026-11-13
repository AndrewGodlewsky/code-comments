import unittest

from notify.batcher import Batcher
from notify.config import BATCH_SIZE, FLUSH_INTERVAL_S
from notify.sender import send_batch


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class Provider:
    def __init__(self):
        self.calls = []

    def push(self, app, notifications):
        self.calls.append((app, notifications))


class BatcherTest(unittest.TestCase):
    def test_full_batch_is_sent_at_once(self):
        sent = []
        batcher = Batcher(sent.append, Clock())
        for i in range(BATCH_SIZE):
            batcher.add(i)
        self.assertEqual([len(b) for b in sent], [BATCH_SIZE])

    def test_partial_batch_waits_for_the_flush_interval(self):
        sent, clock = [], Clock()
        batcher = Batcher(sent.append, clock)
        batcher.add("a")
        clock.now = FLUSH_INTERVAL_S - 1
        batcher.tick()
        self.assertEqual(sent, [])
        clock.now = FLUSH_INTERVAL_S
        batcher.tick()
        self.assertEqual(sent, [["a"]])


class SenderTest(unittest.TestCase):
    def test_one_call_per_batch(self):
        provider = Provider()
        self.assertEqual(send_batch(provider, "ios", ["a", "b"]), 2)
        self.assertEqual(provider.calls, [("ios", ["a", "b"])])


if __name__ == "__main__":
    unittest.main()

import unittest

from notify import config
from notify.batcher import Batcher


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class BatchSizeTest(unittest.TestCase):
    def test_batches_hold_250(self):
        self.assertEqual(config.BATCH_SIZE, 250)
        sent = []
        batcher = Batcher(sent.append, Clock())
        for i in range(249):
            batcher.add(i)
        self.assertEqual(sent, [])
        batcher.add(249)
        self.assertEqual([len(b) for b in sent], [250])

    def test_flush_interval_unchanged(self):
        self.assertEqual(config.FLUSH_INTERVAL_S, 30)
        sent, clock = [], Clock()
        batcher = Batcher(sent.append, clock)
        batcher.add("a")
        clock.now = 29
        batcher.tick()
        self.assertEqual(sent, [])
        clock.now = 30
        batcher.tick()
        self.assertEqual(sent, [["a"]])

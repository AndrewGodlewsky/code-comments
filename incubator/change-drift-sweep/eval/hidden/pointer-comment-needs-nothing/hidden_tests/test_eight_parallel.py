import threading
import time
import unittest

from jobs import limits
from jobs.runner import run_all


class EightParallelTest(unittest.TestCase):
    def test_cap_is_eight(self):
        self.assertEqual(limits.MAX_PARALLEL, 8)

    def test_eight_jobs_run_at_once(self):
        barrier = threading.Barrier(8, timeout=3)
        self.assertEqual(len(run_all([barrier.wait] * 8)), 8)

    def test_never_more_than_eight(self):
        lock, active, peak = threading.Lock(), [0], [0]

        def job():
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            time.sleep(0.05)
            with lock:
                active[0] -= 1

        run_all([job] * 24)
        self.assertLessEqual(peak[0], 8)

    def test_tries_unchanged(self):
        self.assertEqual(limits.MAX_TRIES, 4)

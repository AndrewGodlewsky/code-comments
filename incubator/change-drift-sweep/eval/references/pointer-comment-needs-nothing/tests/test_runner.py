import threading
import time
import unittest

from jobs import limits
from jobs.runner import JobFailed, run_all


class RunAllTest(unittest.TestCase):
    def test_results_in_submission_order(self):
        self.assertEqual(run_all([lambda i=i: i * i for i in range(10)]), [i * i for i in range(10)])

    def test_failing_job_is_tried_max_tries_times(self):
        calls = []

        def broken():
            calls.append(1)
            raise ValueError("no")

        with self.assertRaises(JobFailed):
            run_all([broken])
        self.assertEqual(len(calls), limits.MAX_TRIES)

    def test_concurrency_never_exceeds_the_cap(self):
        lock, active, peak = threading.Lock(), [0], [0]

        def job():
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            time.sleep(0.02)
            with lock:
                active[0] -= 1

        run_all([job] * (limits.MAX_PARALLEL * 3))
        self.assertLessEqual(peak[0], limits.MAX_PARALLEL)


if __name__ == "__main__":
    unittest.main()

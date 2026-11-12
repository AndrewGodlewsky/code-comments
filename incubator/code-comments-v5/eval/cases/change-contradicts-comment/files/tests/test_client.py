import unittest

from geo.client import Throttle
from geo.limits import REQUESTS_PER_MINUTE


class ThrottleTest(unittest.TestCase):
    def test_interval_matches_limit(self):
        self.assertAlmostEqual(Throttle().interval, 60.0 / REQUESTS_PER_MINUTE)

    def test_waits_between_calls(self):
        slept = []
        throttle = Throttle(per_minute=60, clock=lambda: 0.0, sleep=slept.append)
        throttle.wait()
        throttle.wait()
        self.assertEqual(slept, [1.0])


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime

from alerts.spikes import find_spikes
from metrics.readings import Reading
from metrics.rollup import hourly_rollup

SHUFFLED = [
    Reading("t1", datetime(2026, 11, 1, 10, 30), 3.0),
    Reading("t2", datetime(2026, 11, 1, 10, 0), 8.0),
    Reading("t1", datetime(2026, 11, 1, 10, 0), 1.0),
    Reading("t1", datetime(2026, 11, 1, 11, 0), 5.0),
]


class RollupTest(unittest.TestCase):
    def test_rollup_accepts_readings_in_any_order(self):
        self.assertEqual(hourly_rollup(SHUFFLED), {
            ("t1", datetime(2026, 11, 1, 10)): 2.0,
            ("t2", datetime(2026, 11, 1, 10)): 8.0,
            ("t1", datetime(2026, 11, 1, 11)): 5.0,
        })

    def test_small_changes_are_not_spikes(self):
        self.assertEqual(find_spikes(SHUFFLED), [])


if __name__ == "__main__":
    unittest.main()

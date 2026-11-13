import unittest
from datetime import datetime, timedelta

from notify.digest import due

NOW = datetime(2026, 5, 4, 8, 0)


class GapTest(unittest.TestCase):
    def test_gap_is_six_hours(self):
        self.assertFalse(due(NOW - timedelta(hours=5, minutes=59), NOW))
        self.assertTrue(due(NOW - timedelta(hours=6), NOW))
        self.assertTrue(due(NOW - timedelta(hours=7), NOW))

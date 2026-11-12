import unittest

from pumps.metrics import StationMetrics
from pumps.telemetry import apply_feed


class StationMetricsTest(unittest.TestCase):
    def test_counts_starts_per_station(self):
        metrics = StationMetrics()
        apply_feed(metrics, ["north START P1", "north START P2", "east START P1"])
        text = metrics.render()
        self.assertIn('{station="north"} 2', text)
        self.assertIn('{station="east"} 1', text)

    def test_keeps_the_latest_level(self):
        metrics = StationMetrics()
        apply_feed(metrics, ["north LEVEL 1.84", "", "north LEVEL 1.91"])
        self.assertIn('{station="north"} 1.91', metrics.render())
        self.assertNotIn("1.84", metrics.render())


if __name__ == "__main__":
    unittest.main()

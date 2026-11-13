import os
import tempfile
import unittest
from datetime import datetime

from metrics.readings import load_readings, parse_line

LINES = "t2,2026-11-01T10:05:00,4.0\nt1,2026-11-01T10:00:00,1.5\nt1,2026-11-01T09:00:00,2.5\n"


class ReadingsTest(unittest.TestCase):
    def test_parse_line(self):
        reading = parse_line("t1,2026-11-01T10:00:00,1.5\n")
        self.assertEqual((reading.sensor, reading.at, reading.value), ("t1", datetime(2026, 11, 1, 10), 1.5))

    def test_load_returns_every_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "readings.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(LINES + "\n")
            self.assertEqual(sorted(reading.value for reading in load_readings(path)), [1.5, 2.5, 4.0])


if __name__ == "__main__":
    unittest.main()

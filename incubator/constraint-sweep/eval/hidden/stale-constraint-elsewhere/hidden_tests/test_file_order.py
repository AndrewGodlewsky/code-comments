import os
import tempfile
import unittest
from datetime import datetime

from alerts.spikes import find_spikes
from metrics.readings import load_readings
from metrics.rollup import hourly_rollup

FILE = "\n".join([
    "t2,2026-11-01T10:05:00,4.0",
    "t1,2026-11-01T10:40:00,30.0",
    "t1,2026-11-01T10:00:00,2.0",
    "t2,2026-11-01T09:55:00,3.0",
    "t1,2026-11-01T10:20:00,4.0",
]) + "\n"


def at(hour, minute=0):
    return datetime(2026, 11, 1, hour, minute)


class FileOrderTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, "readings.csv")
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(FILE)

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_keeps_file_order(self):
        self.assertEqual([(reading.sensor, reading.at) for reading in load_readings(self.path)],
                         [("t2", at(10, 5)), ("t1", at(10, 40)), ("t1", at(10)), ("t2", at(9, 55)),
                          ("t1", at(10, 20))])

    def test_consumers_are_still_correct(self):
        readings = load_readings(self.path)
        self.assertEqual(hourly_rollup(readings), {("t1", at(10)): 12.0, ("t2", at(10)): 4.0, ("t2", at(9)): 3.0})
        self.assertEqual(find_spikes(readings), [("t1", at(10, 40))])


if __name__ == "__main__":
    unittest.main()

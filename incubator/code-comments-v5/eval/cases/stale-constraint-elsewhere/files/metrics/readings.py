"""Parse sensor readings files.

A readings file has one "sensor,timestamp,value" line per reading. Timestamps are
ISO 8601 in UTC. Gateways upload in batches, so lines are not in time order.
"""
from collections import namedtuple
from datetime import datetime

Reading = namedtuple("Reading", "sensor at value")


def parse_line(line):
    """Parse one "sensor,timestamp,value" line."""
    sensor, stamp, value = line.strip().split(",")
    return Reading(sensor, datetime.fromisoformat(stamp), float(value))


def load_readings(path):
    """Return every reading in the file."""
    with open(path, encoding="utf-8") as fh:
        readings = [parse_line(line) for line in fh if line.strip()]
    readings.sort(key=lambda reading: (reading.sensor, reading.at))
    return readings

"""Hourly rollups per sensor."""
from itertools import groupby


def _sensor_hour(reading):
    return reading.sensor, reading.at.replace(minute=0, second=0, microsecond=0)


def hourly_rollup(readings):
    """Return {(sensor, hour): mean value}."""
    # groupby only groups adjacent items, so sort by sensor and time first.
    ordered = sorted(readings, key=lambda reading: (reading.sensor, reading.at))
    result = {}
    for key, group in groupby(ordered, key=_sensor_hour):
        values = [reading.value for reading in group]
        result[key] = sum(values) / len(values)
    return result

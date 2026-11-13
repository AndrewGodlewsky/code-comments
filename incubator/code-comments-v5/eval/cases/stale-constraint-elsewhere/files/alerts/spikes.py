"""Flag sudden jumps between a sensor's consecutive readings."""

JUMP = 10.0


def find_spikes(readings, jump=JUMP):
    """Return (sensor, at) for each reading more than jump away from the sensor's previous one."""
    spikes = []
    last = {}
    for reading in sorted(readings, key=lambda reading: reading.at):
        previous = last.get(reading.sensor)
        if previous is not None and abs(reading.value - previous) > jump:
            spikes.append((reading.sensor, reading.at))
        last[reading.sensor] = reading.value
    return spikes

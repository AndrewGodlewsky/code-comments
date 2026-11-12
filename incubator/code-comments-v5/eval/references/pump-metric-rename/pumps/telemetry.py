"""Turn the station controllers' event lines into metric updates."""


def apply_event(metrics, line):
    """Apply one controller line, such as "north START P2" or "north LEVEL 1.84"."""
    station, kind, value = line.split()
    if kind == "START":
        metrics.pump_started(station)
    elif kind == "LEVEL":
        metrics.set_level(station, float(value))


def apply_feed(metrics, lines):
    for line in lines:
        if line.strip():
            apply_event(metrics, line)

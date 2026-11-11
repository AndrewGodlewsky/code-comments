"""Print the hourly rollup and any spikes: python -m cli.report READINGS"""
import sys

from alerts.spikes import find_spikes
from metrics.readings import load_readings
from metrics.rollup import hourly_rollup


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    readings = load_readings(argv[0])
    for (sensor, hour), mean in sorted(hourly_rollup(readings).items()):
        print(f"{sensor} {hour:%Y-%m-%d %H:00} {mean:.2f}")
    for sensor, at in find_spikes(readings):
        print(f"SPIKE {sensor} {at:%Y-%m-%d %H:%M}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

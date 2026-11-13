"""Dump parsed readings as JSON lines: python -m cli.export READINGS OUT"""
import json
import sys

from metrics.readings import load_readings


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    source, target = argv
    with open(target, "w", encoding="utf-8") as out:
        # Line order does not matter: the dashboard indexes readings by sensor and time.
        for reading in load_readings(source):
            out.write(json.dumps({"sensor": reading.sensor, "at": reading.at.isoformat(),
                                  "value": reading.value}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

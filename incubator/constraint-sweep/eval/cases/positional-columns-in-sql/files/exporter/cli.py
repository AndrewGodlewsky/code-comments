"""Write tonight's export: python -m exporter.cli OUT.csv < records.json"""
import json
import sys

from exporter.csv_out import write_csv
from exporter.rows import cleared_entries


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    records = json.load(sys.stdin)
    with open(argv[0], "w", newline="", encoding="utf-8") as fh:
        write_csv(cleared_entries(records), fh)
    return 0


if __name__ == "__main__":
    sys.exit(main())

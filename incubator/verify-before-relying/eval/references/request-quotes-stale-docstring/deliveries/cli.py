"""Print the date an order placed on a given day should arrive.

Usage: python -m deliveries.cli DATE
"""

import sys

from deliveries.dates import parse_date
from deliveries.estimate import delivery_date


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        ordered = parse_date(argv[0])
    except ValueError:
        ordered = None
    if ordered is None:
        print("invalid date", file=sys.stderr)
        return 2
    print(delivery_date(ordered).isoformat())
    return 0


if __name__ == "__main__":
    sys.exit(main())

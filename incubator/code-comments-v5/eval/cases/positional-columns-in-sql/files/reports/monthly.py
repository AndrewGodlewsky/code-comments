"""Monthly totals per account, read from the nightly export files."""
import csv
from collections import defaultdict
from decimal import Decimal


def monthly_totals(paths):
    """Return {account: Decimal total} over the given nightly CSV files."""
    totals = defaultdict(Decimal)
    for path in paths:
        with open(path, newline="", encoding="utf-8") as fh:
            # Columns are found by header name, so their order does not matter here.
            for row in csv.DictReader(fh):
                totals[row["account"]] += Decimal(row["amount"])
    return dict(totals)

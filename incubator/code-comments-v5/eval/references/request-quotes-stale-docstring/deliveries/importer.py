"""Read the warehouse's order sheet: a CSV with order_id and ordered columns."""

import csv

from deliveries.dates import parse_date


def read_orders(handle):
    """Return (orders, skipped).

    orders maps each order_id to its order date. A row whose ordered cell holds no date
    yet (blank, or a note such as "tbc") is left out. skipped lists the line numbers whose
    date does not exist, such as 31/02/2026, so the warehouse can correct the typo.
    """
    orders, skipped = {}, []
    for line_no, row in enumerate(csv.DictReader(handle), start=2):
        try:
            ordered = parse_date(row["ordered"])
        except ValueError:
            skipped.append(line_no)
            continue
        if ordered is not None:
            orders[row["order_id"]] = ordered
    return orders, skipped

"""Read the warehouse's order sheet: a CSV with order_id and ordered columns."""

import csv

from deliveries.dates import parse_date


def read_orders(handle):
    """Return (orders, skipped).

    orders maps each order_id to its order date. skipped lists the line numbers whose
    ordered cell holds no date the tools can use: blank, a note such as "tbc", or a date
    that does not exist, such as 31/02/2026.
    """
    orders, skipped = {}, []
    for line_no, row in enumerate(csv.DictReader(handle), start=2):
        ordered = parse_date(row["ordered"])
        if ordered is None:
            skipped.append(line_no)
            continue
        orders[row["order_id"]] = ordered
    return orders, skipped

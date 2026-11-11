"""Read supplier price files."""

import csv


def read_rows(path):
    """Return each data row of the CSV file at path as a dict keyed by the header row."""
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def is_blank(row):
    return all(not (value or "").strip() for value in row.values())


def parse_price(text):
    """Return the price in cents. Accepts "12.50" and "12,50"."""
    whole, _, fraction = text.strip().replace(",", ".").partition(".")
    return int(whole) * 100 + int((fraction + "00")[:2])


def clean(rows):
    """Drop blank rows and convert each price to cents."""
    return [dict(row, price=parse_price(row["price"])) for row in rows if not is_blank(row)]

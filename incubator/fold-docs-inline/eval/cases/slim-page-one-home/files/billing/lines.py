"""Invoice lines built from an order."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Line:
    sku: str
    description: str
    amount: Decimal


def invoice_lines(order):
    """Return the order's items as invoice lines."""
    lines = [Line(item["sku"], item["description"], Decimal(item["amount"])) for item in order["items"]]
    return sorted(lines, key=lambda line: line.sku)

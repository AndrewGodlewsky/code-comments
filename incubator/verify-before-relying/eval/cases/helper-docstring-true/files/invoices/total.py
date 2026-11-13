"""Invoice totals."""

from decimal import Decimal


def invoice_total(lines):
    """Return the invoice total: quantity times unit price, summed over the lines."""
    return sum((line.quantity * line.unit_price for line in lines), Decimal("0"))

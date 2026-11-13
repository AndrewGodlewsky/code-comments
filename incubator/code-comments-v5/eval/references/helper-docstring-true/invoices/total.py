"""Invoice totals."""

from decimal import Decimal

from money.rounding import round_cents


def invoice_total(lines):
    """Return the invoice total: quantity times unit price, summed over the lines, rounded
    half up to the cent as the tax office requires."""
    return round_cents(sum((line.quantity * line.unit_price for line in lines), Decimal("0")))

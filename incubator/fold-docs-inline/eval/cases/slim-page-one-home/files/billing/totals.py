"""Invoice totals."""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def invoice_total(lines):
    """Return the invoice total in euros, rounded to the cent."""
    total = sum((line.amount for line in lines), Decimal("0"))
    return total.quantize(CENT, rounding=ROUND_HALF_UP)

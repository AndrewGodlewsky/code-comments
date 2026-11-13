"""Invoice totals."""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def invoice_total(lines):
    """Return the invoice total for (quantity, unit_price) lines.

    Each line is rounded to the cent before the lines are added, because the
    printed invoice shows rounded line amounts and the total must match them.
    """
    total = Decimal("0")
    for quantity, unit_price in lines:
        amount = Decimal(quantity) * Decimal(unit_price)
        total += amount.quantize(CENT, rounding=ROUND_HALF_UP)
    return total

"""Invoice totals."""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def invoice_total(lines):
    """Return the invoice total in euros, rounded to the cent."""
    total = sum((line.amount for line in lines), Decimal("0"))
    # Half-up, not Python's default half-even: the tax office's e-invoice validator
    # rejects totals rounded half-even (FIN-88).
    return total.quantize(CENT, rounding=ROUND_HALF_UP)

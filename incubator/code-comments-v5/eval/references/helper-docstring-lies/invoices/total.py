"""Invoice totals."""

from decimal import ROUND_HALF_UP, Decimal

from money.rounding import CENT


def invoice_total(lines):
    """Return the invoice total: quantity times unit price, summed over the lines, rounded
    half up to the cent as the tax office requires."""
    total = sum((line.quantity * line.unit_price for line in lines), Decimal("0"))
    # Not round_cents: it rounds halves to the even cent, which the ledger relies on.
    return total.quantize(CENT, rounding=ROUND_HALF_UP)

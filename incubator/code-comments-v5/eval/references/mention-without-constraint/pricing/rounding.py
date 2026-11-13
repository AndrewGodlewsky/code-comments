"""Money rounding for the shop. Every amount is rounded here, nowhere else."""
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
FIVE_RAPPEN = Decimal("0.05")


def round_price(amount, currency=None):
    """Round a Decimal amount to the cent, with halves rounding up.

    For "CHF", round to the nearest 0.05 instead, again with halves rounding up.
    """
    if currency == "CHF":
        steps = (amount / FIVE_RAPPEN).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return (steps * FIVE_RAPPEN).quantize(CENT)
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)

"""Money rounding for the shop. Every amount is rounded here, nowhere else."""
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def round_price(amount):
    """Round a Decimal amount to the cent, with halves rounding up."""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)

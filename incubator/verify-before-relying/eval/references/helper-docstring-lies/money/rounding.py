"""Rounding for money amounts held as Decimal."""

from decimal import Decimal

CENT = Decimal("0.01")


def round_cents(amount):
    """Round amount to the nearest cent, rounding halves to the even cent."""
    return amount.quantize(CENT)

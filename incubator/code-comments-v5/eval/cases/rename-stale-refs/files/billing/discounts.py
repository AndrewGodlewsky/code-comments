"""Discounts applied to invoice lines."""

from decimal import Decimal


def apply_discount(lines, percent):
    """Return lines with each unit price reduced by percent.

    Apply this before `compute_total`, so the rounding happens on the
    discounted prices.
    """
    factor = (Decimal(100) - Decimal(percent)) / Decimal(100)
    return [(q, Decimal(p) * factor) for q, p in lines]

"""Daily sales totals."""
from decimal import Decimal

from pricing.rounding import round_price


def daily_total(line_totals):
    """Return the sum of the day's invoice line totals.

    Totals use round_price too, so they match the sum of the invoice lines to the cent.
    """
    return round_price(sum(line_totals, Decimal("0")))

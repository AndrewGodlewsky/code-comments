"""Invoice line totals."""
from decimal import Decimal

from pricing.rounding import round_price


def line_total(unit_price, quantity):
    """Return the total for one invoice line.

    The product is rounded once with round_price, not unit by unit, so ten items at
    0.333 come to 3.33 rather than 3.30.
    """
    return round_price(Decimal(unit_price) * quantity)

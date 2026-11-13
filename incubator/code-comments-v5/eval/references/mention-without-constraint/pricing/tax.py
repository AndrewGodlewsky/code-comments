"""VAT on shop prices."""
from decimal import Decimal

from pricing.rounding import round_price

VAT_RATE = Decimal("0.20")


def add_vat(net):
    """Return the gross price for a net Decimal price, rounded once with round_price."""
    return round_price(net * (1 + VAT_RATE))

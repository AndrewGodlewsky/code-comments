"""Money helpers shared by the event handlers and the payout run."""
from decimal import ROUND_HALF_UP, Decimal


def pence(amount):
    """Convert an amount in pounds (a string, int or Decimal) to whole pence."""
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

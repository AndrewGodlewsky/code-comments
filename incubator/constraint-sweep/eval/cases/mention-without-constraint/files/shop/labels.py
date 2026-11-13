"""Price labels for the shop front."""
from decimal import Decimal

from pricing.rounding import round_price


def price_label(amount, symbol="$"):
    """Return a label such as "$1,234.50"."""
    # Display prices pass through round_price before formatting, so a label never
    # shows a fraction of a cent.
    return f"{symbol}{round_price(Decimal(amount)):,.2f}"

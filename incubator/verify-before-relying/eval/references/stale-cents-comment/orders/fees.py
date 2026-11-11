"""Fees added to an order at checkout."""

from decimal import Decimal

CARD_FEE = Decimal("0.30")


def add_card_fee(order):
    """Add the card processing fee to the order total and return the order."""
    order.total += CARD_FEE
    return order

"""Fees added to an order at checkout."""

CARD_FEE = 30


def add_card_fee(order):
    """Add the card processing fee to the order total and return the order."""
    order.total += CARD_FEE
    return order

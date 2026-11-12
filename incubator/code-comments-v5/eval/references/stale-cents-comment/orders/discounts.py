"""Discounts taken off an order before payment."""


def apply_discount(order, percent):
    """Take percent (0 to 100) off the order total and return the order."""
    if not 0 <= percent <= 100:
        raise ValueError(f"percent must be between 0 and 100, got {percent}")
    order.total = order.total * (100 - percent) / 100
    return order

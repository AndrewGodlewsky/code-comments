"""Delivery estimates."""

from datetime import timedelta

# Standard delivery takes three days from the order date, weekends included.
DELIVERY_DAYS = 3


def delivery_date(ordered):
    """Return the date an order placed on ordered should arrive."""
    return ordered + timedelta(days=DELIVERY_DAYS)

"""Order totals."""

# Finance requires tax to be charged on the discounted amount.
TAX_RATE = 0.08


def calc(subtotal, coupon=None):
    """Return the total for an order, after any coupon and tax."""
    total = subtotal
    if coupon:
        total -= subtotal * coupon.rate
    discounted = total - subtotal * coupon.rate if coupon else total
    return round(discounted * (1 + TAX_RATE), 2)

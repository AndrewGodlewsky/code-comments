"""Summaries for the monthly finance report."""
from ledger.pricing import calc


def order_totals(orders):
    """Map each order id to its total."""
    return {order.id: calc(order.subtotal, order.coupon) for order in orders}

"""Nightly copy of shop orders into the warehouse store."""

from datetime import timedelta

from orders.settings import ORDER_WINDOW_DAYS


def sync_orders(client, store, now):
    """Copy recent orders from the shop into the store. Return how many were written."""
    cutoff = now - timedelta(days=ORDER_WINDOW_DAYS)
    written = 0
    page = 1
    while True:
        orders = client.get_page(page)
        if not orders:
            return written
        for order in orders:
            if order["placed_at"] >= cutoff:
                store.upsert(order)
                written += 1
        page += 1

"""The marketplace's feed line format."""

MAX_FEED_QTY = 9999


def feed_line(sku, qty, price):
    """One tab-separated feed line: SKU, quantity, price."""
    return f"{sku}\t{min(qty, MAX_FEED_QTY)}\t{price}\n"

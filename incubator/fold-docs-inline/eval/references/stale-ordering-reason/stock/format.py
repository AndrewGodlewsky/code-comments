"""The marketplace's feed line format."""

# The marketplace's feed format has a four-digit quantity column and rejects the whole
# file if any value is longer (MKT-204).
MAX_FEED_QTY = 9999


def feed_line(sku, qty, price):
    """One tab-separated feed line: SKU, quantity, price."""
    return f"{sku}\t{min(qty, MAX_FEED_QTY)}\t{price}\n"

"""Writes the marketplace stock feed."""

from stock.format import feed_line


def write_feed(rows, prices, out):
    """Write one line per stocked SKU that has a price.

    rows and prices are (sku, value) pairs. The two lists are walked together in a
    single merge pass, so a SKU missing from either side is passed over.
    """
    prices = iter(sorted(prices))
    price_sku, price = next(prices, (None, None))
    for sku, qty in sorted(rows):
        while price_sku is not None and price_sku < sku:
            price_sku, price = next(prices, (None, None))
        if price_sku == sku:
            out.write(feed_line(sku, qty, price))

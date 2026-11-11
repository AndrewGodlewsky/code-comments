"""Stock levels for the marketplace feed."""


def stock_rows(levels):
    """Return (sku, quantity) pairs for every SKU in stock."""
    return sorted((sku, qty) for sku, qty in levels.items() if qty > 0)

"""Reserve warehouse stock for orders."""


class InsufficientStock(Exception):
    def __init__(self, sku, requested, available):
        super().__init__(f"{sku}: requested {requested}, only {available} available")
        self.sku = sku
        self.requested = requested
        self.available = available


def reserve(stock, sku, qty):
    """Reserve ``qty`` units of ``sku`` from ``stock``.

    Returns True if the units were reserved, or False if there is not enough
    stock, in which case ``stock`` is left unchanged.
    """
    # A zero or negative quantity would reserve nothing or, worse, silently add
    # units back to stock, so treat it as a caller bug.
    if type(qty) is not int or qty <= 0:
        raise ValueError(f"quantity must be a positive integer: {qty!r}")
    available = stock.get(sku, 0)
    if available < qty:
        return False
    stock[sku] = available - qty
    return True

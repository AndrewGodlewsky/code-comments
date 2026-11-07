"""Reserve warehouse stock for orders, and return it when orders are cancelled."""


class InsufficientStock(Exception):
    def __init__(self, sku, requested, available):
        super().__init__(f"{sku}: requested {requested}, only {available} available")
        self.sku = sku
        self.requested = requested
        self.available = available


def reserve(stock, sku, qty):
    """Reserve ``qty`` units of ``sku`` from ``stock`` and return the units left.

    Raises InsufficientStock if there is not enough stock, in which case
    ``stock`` is left unchanged.
    """
    # A zero or negative quantity would reserve nothing or, worse, silently add
    # units back to stock, so treat it as a caller bug.
    _check_quantity(qty)
    available = stock.get(sku, 0)
    if available < qty:
        raise InsufficientStock(sku, qty, available)
    stock[sku] = available - qty
    return stock[sku]


def release(stock, sku, qty):
    """Return ``qty`` units of ``sku`` to ``stock`` and return the units now in stock.

    A sku with no entry in ``stock`` starts from zero.
    """
    # A negative quantity would silently remove units from stock, so it is a
    # caller bug here just as it is in reserve.
    _check_quantity(qty)
    stock[sku] = stock.get(sku, 0) + qty
    return stock[sku]


def _check_quantity(qty):
    # bool is a subclass of int, so compare the exact type.
    if type(qty) is not int or qty <= 0:
        raise ValueError(f"quantity must be a positive integer: {qty!r}")

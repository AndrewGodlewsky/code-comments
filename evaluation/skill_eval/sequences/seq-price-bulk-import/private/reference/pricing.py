"""Change catalogue prices."""


class PriceError(ValueError):
    """A price the catalogue cannot store."""


def _validate(sku, cents):
    if type(cents) is not int or cents <= 0:
        raise PriceError(f"price for {sku} must be a positive number of cents: {cents!r}")


def set_price(store, cache, sku, cents):
    """Set ``sku`` to ``cents`` and return the previous price (None if new)."""
    _validate(sku, cents)
    previous = store.get(sku)
    store.put(sku, cents)
    # Invalidate only after the store write: a page view that misses the cache
    # refills it from the store, so deleting first lets a concurrent view
    # re-cache the old price for the full 24-hour TTL.
    cache.delete(sku)
    return previous


def set_prices(store, cache, prices):
    """Set many prices in two round trips; return each SKU's previous price (None if new).

    Nothing is written or invalidated unless every price in the batch is valid.
    """
    for sku, cents in prices.items():
        _validate(sku, cents)
    previous = {sku: store.get(sku) for sku in prices}
    store.put_many(prices)
    # Same order as set_price, for the same reason: invalidate only after the
    # whole batch is in the store, or a page view that misses in between would
    # refill the cache with an old price for 24 hours.
    cache.delete_many(list(prices))
    return previous

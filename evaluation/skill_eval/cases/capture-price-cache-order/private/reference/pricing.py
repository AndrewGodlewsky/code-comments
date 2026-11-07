"""Change catalogue prices."""


class PriceError(ValueError):
    """A price the catalogue cannot store."""


def set_price(store, cache, sku, cents):
    """Set ``sku`` to ``cents`` and return the previous price (None if new)."""
    if type(cents) is not int or cents <= 0:
        raise PriceError(f"price for {sku} must be a positive number of cents: {cents!r}")
    previous = store.get(sku)
    store.put(sku, cents)
    # Invalidate only after the store write: a page view that misses the cache
    # refills it from the store, so deleting first lets a concurrent view
    # re-cache the old price for the full 24-hour TTL.
    cache.delete(sku)
    return previous

# Batch price updates for the nightly catalogue import

The nightly catalogue import changes thousands of prices by calling `set_price`
once per SKU, which costs two network round trips per SKU. The store client now
has `put_many(prices)` and the page cache client has `delete_many(skus)`; each
handles its whole batch in a single round trip.

Add `set_prices(store, cache, prices)` to `pricing.py`. `prices` is a dict
mapping SKU to cents. It should:

- validate every price the way `set_price` does, and raise `PriceError` without
  writing or invalidating anything if any price in the batch is invalid;
- write all the new prices with one `store.put_many(prices)` call;
- invalidate the page cache entries of all those SKUs with one
  `cache.delete_many(skus)` call;
- return a dict mapping each SKU to what it cost beforehand (`None` for a SKU
  that had no price yet), read with `store.get`.

`set_price` must keep working as it does today; the storefront's admin screen
still uses it for single edits.

# Invalidate the page cache when a price changes

Product pages keep showing the old price for up to a day after we change it
(see `docs/incident-0917.md`). Make `set_price` invalidate the product's page
cache entry with `cache.delete(sku)` so new prices show up straight away.

Every call site already passes the page cache as the second argument; it just
isn't used yet. Keep the validation and the return value as they are.

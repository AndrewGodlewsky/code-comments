# Incident 0917: product pages showed old prices for up to a day

**Summary (catalogue on-call):** After a price change, product pages kept
showing the previous price until the page cache entry expired. Page cache
entries live for 24 hours. `set_price` writes the price store and never touches
the page cache.

**First theory (support):** the CDN is caching product pages. Checked and ruled
out: price fragments are served with `Cache-Control: no-store`, and the CDN logs
show no cache hits for them. The stale prices come from our own page cache.

**Fix notes (Dana, catalogue):** Delete the SKU's page cache entry in
`set_price`, but mind the order. Product pages read through the page cache: on
a miss they load the price from the store and cache it for the full 24 hours.
If we delete the entry before the store write lands, a page view in between
misses, reads the *old* price from the store and caches it again for another
day. We reproduced exactly that in the load test. Write the store first, then
delete the cache entry.

The page cache client exposes `get(key)`, `set(key, value, ttl)` and
`delete(key)`. Deleting a key that is not cached is a no-op.

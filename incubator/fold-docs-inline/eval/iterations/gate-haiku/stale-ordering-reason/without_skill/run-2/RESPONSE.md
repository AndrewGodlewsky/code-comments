I removed docs/stock-feed.md and moved its content into the code next to what it describes. Nothing on the page needed to stay a document.

What moved and where:
- Zero-stock SKUs are left out: docstring of `stock_rows()` in stock/rows.py.
- Rows are sorted by SKU: also in the `stock_rows()` docstring, with the reason corrected (see below).
- Tab-separated line format: already stated in the `feed_line()` docstring in stock/format.py, so nothing was added.
- Quantity cap and its reason (four-digit column, whole file rejected, MKT-204): comment above `MAX_FEED_QTY` in stock/format.py.

One claim was wrong and I did not carry it over. The page said `write_feed()` walks rows and prices in a single merge pass, so unsorted rows are silently skipped. It does not. `write_feed()` looks up each price by SKU with `prices.get(sku)`, so row order does not matter. I documented that in the `write_feed()` docstring in stock/feed.py. The sort in `stock_rows()` is kept (behaviour unchanged) and is described as giving a stable output order. If the sort is only needed for that reason, it could be removed, but I did not change the behaviour.

No code behaviour changed. The three unit tests pass (`python -I -m unittest discover -s tests -t .`). No other file referenced docs/stock-feed.md. docs/marketplace.md is unchanged; it holds marketplace facts (SFTP pickup time, seller support contact) that are not about the code, so it stays a document.

Not done: there is no test that pins the order-independence of `write_feed()`. Adding one would protect the corrected claim.

I removed docs/stock-feed.md. Nothing on it needed to stay a document, and nothing else in the repo linked to it.

Where each item went:
- **Skips SKUs with no stock:** this was already in the `stock_rows()` docstring, so I added nothing.
- **Tab-separated SKU, quantity, price:** this was already in the `feed_line()` docstring, so I added nothing.
- **Quantity cap and the MKT-204 reason:** I added a comment above `MAX_FEED_QTY` in `stock/format.py`. It says the marketplace's four-digit quantity column rejects the whole file if any value is longer.
- **Rows must be sorted by SKU:** I did not carry this over, because it is no longer true. `write_feed()` sorts both `rows` and `prices` itself before the merge pass, so unsorted input is not skipped. I added a short comment in `stock/feed.py` saying callers need not pass SKU order. `stock_rows()` still returns sorted rows, but nothing depends on it.

I didn't run the tests. `docs/marketplace.md` is untouched.

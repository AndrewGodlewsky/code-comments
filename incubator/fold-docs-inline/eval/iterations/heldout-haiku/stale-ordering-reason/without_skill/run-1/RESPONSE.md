I removed docs/stock-feed.md and moved its content into the code it describes. Nothing on the page needed to stay a document. The three unit tests pass.

Where each bullet went:

- "stock_rows() leaves out SKUs that have no stock": now in the `stock_rows` docstring in stock/rows.py. The zero-or-less check is already tested in tests/test_feed.py.
- "Each feed line is tab-separated: SKU, quantity and price": already in the `feed_line` docstring in stock/format.py, so nothing new was needed.
- "Quantities are capped at MAX_FEED_QTY (9999) ... rejects the whole file ... (MKT-204)": now a comment above `MAX_FEED_QTY` in stock/format.py, keeping the reason and the ticket reference. The cap is already covered by test_line_caps_quantity.
- "stock_rows() must return rows sorted by SKU ... a row that arrives out of order is silently skipped": dropped as a requirement. It was stale. `write_feed` already sorts both `rows` and `prices` before its merge pass, so callers do not need to supply sorted input. The `write_feed` docstring now says that, and `stock_rows` documents that it returns sorted output without presenting that as a requirement.

Other changes: none to behaviour. Nothing else in the repo referred to docs/stock-feed.md (checked with grep), so no links were broken. docs/marketplace.md is unchanged and still the only page under docs/.

I folded docs/stock-feed.md into the code and deleted the page, since nothing on it needed to stay a document. One claim was not migrated because the code contradicts it, and I need your call on it.

Fate list, in page order:
1. "`stock_rows()` leaves out SKUs that have no stock." Dropped. The `stock_rows` docstring in stock/rows.py ("every SKU in stock") and its `qty > 0` filter state it, and `test_rows_skip_empty_stock` covers it.
2. "`stock_rows()` must return rows sorted by SKU": Not migrated. Nothing in the code relies on it. `write_feed` in stock/feed.py calls `sorted(rows)` and `sorted(prices)` itself, so out-of-order rows are not skipped. The page's rule is false as the code stands, so I put it in no comment.
3. "`write_feed()` walks the rows and the price list together in a single merge pass": Dropped. The `write_feed` docstring already says this.
4. "a row that arrives out of order is silently skipped": Not migrated, for the same reason as line 2. The sort inside `write_feed` prevents it. Which side is right: is the page stale, or is the internal sort meant to go? If the sort is meant to go, the ordering rule would need to be moved as a comment at that point.
5. "Each feed line is tab-separated: SKU, quantity and price." Dropped. The `feed_line` docstring and f-string in stock/format.py state it.
6. "Quantities are capped at `MAX_FEED_QTY` (9999)": Dropped. `min(qty, MAX_FEED_QTY)` in `feed_line` and `test_line_caps_quantity` show it. The value 9999 is taken from the code.
7. "because the marketplace's feed format has a four-digit quantity column and rejects the whole file if any value is longer (MKT-204)": Moved. It is now a comment above `MAX_FEED_QTY` in stock/format.py, keeping MKT-204.

Other files:
- Nothing else states the moved fact. docs/marketplace.md and README.md do not mention the cap or the ordering.
- Nothing links to docs/stock-feed.md.
- No gaps for you to fill.
- The page is deleted, as every claim on it has a fate other than kept. No code, tests or other files changed.

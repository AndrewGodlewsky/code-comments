I folded docs/stock-feed.md into the code and deleted the page. Nothing on it needed to stay a document. Every claim has one fate, and one claim is contradicted by the code, so I did not carry it over.

Fate list (page order):

1. "`stock_rows()` leaves out SKUs that have no stock." Dropped. stock/rows.py `if qty > 0` states it, and tests/test_feed.py `test_rows_skip_empty_stock` covers it.
2. "`stock_rows()` must return rows sorted by SKU." Moved. stock/rows.py, `stock_rows` docstring: "Rows must stay sorted by SKU." The page's stated reason is not carried over (see line 4).
3. "`write_feed()` walks the rows and the price list together in a single merge pass." Dropped. The stock/feed.py `write_feed` docstring already says this.
4. "A row that arrives out of order is silently skipped." Not migrated. stock/feed.py:14 is `for sku, qty in sorted(rows):`, so `write_feed` sorts its own input and an out-of-order row is not skipped. The sorting reason in line 2 therefore has no support in the code. Which side is right is your call.
5. "Each feed line is tab-separated: SKU, quantity and price." Dropped. stock/format.py `feed_line` docstring and f-string state it.
6. "Quantities are capped at `MAX_FEED_QTY` (9999)." Dropped. stock/format.py:3 defines the value 9999, `feed_line` applies `min(...)`, and tests/test_feed.py `test_line_caps_quantity` covers it.
7. "...because the marketplace's feed format has a four-digit quantity column and rejects the whole file if any value is longer (MKT-204)." Moved. stock/format.py, comment above `MAX_FEED_QTY`, keeping MKT-204. A one-line pointer sits in `feed_line`, because removing its `min()` alone would break the cap.

Edits:
- stock/rows.py: added "Rows must stay sorted by SKU." to the `stock_rows` docstring.
- stock/format.py: added the marketplace comment above `MAX_FEED_QTY` and a one-line pointer in `feed_line`.
- docs/stock-feed.md: deleted. No claim remained that needed to stay a document.
- Nothing else changed. docs/marketplace.md and README.md are untouched.

Other files: none states a moved fact, and no file links to docs/stock-feed.md.

Gaps for you to decide or fill:
- Line 4 conflicts with the code. If the sort requirement in line 2 no longer matters, the `stock_rows` docstring line can be removed.
- The four-digit marketplace limit (line 7) is a fact about another system. I could not verify it from this repository, so it is recorded as written. Please confirm it with the marketplace, and confirm that MKT-204 is still the right ticket.

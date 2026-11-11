I deleted docs/stock-feed.md. One claim moved into a comment, one is not migrated because the code contradicts it, and nothing needed to stay as a document.

Fate list, in page order:

1. "`stock_rows()` leaves out SKUs that have no stock." Dropped. The `qty > 0` filter and the `stock_rows` docstring in stock/rows.py say it, and `test_rows_skip_empty_stock` covers it.
2. "`stock_rows()` must return rows sorted by SKU." This is split into three parts.
   - It returns rows sorted by SKU. Dropped, because stock/rows.py wraps the result in `sorted(...)`.
   - "`write_feed()` walks the rows and the price list together in a single merge pass." Dropped. The `write_feed` docstring in stock/feed.py already says it.
   - The "must" and "a row that arrives out of order is silently skipped" part. **Not migrated.** `write_feed` in stock/feed.py runs `sorted(rows)` and `sorted(prices)` itself before the merge, so out-of-order input is not skipped, and the code puts no ordering requirement on `stock_rows()`. I wrote no comment and changed no code. Which side is right is your call. If the page was right, `write_feed` should not sort its inputs. If the code is right, the page was stale.
3. "Each feed line is tab-separated: SKU, quantity and price." Dropped. The `feed_line` docstring and f-string in stock/format.py state it, and `test_line_caps_quantity` checks it.
4. "Quantities are capped at `MAX_FEED_QTY` (9999)", with the reason and MKT-204. This is split into two parts.
   - The cap itself and the value 9999. Dropped. `min(qty, MAX_FEED_QTY)` and the `MAX_FEED_QTY = 9999` constant in stock/format.py state them, and a test covers the cap.
   - The reason: the marketplace's feed format has a four-digit quantity column and rejects the whole file if any value is longer (MKT-204). **Moved** to a comment above `MAX_FEED_QTY` in stock/format.py. The comment does not repeat the value, which comes from the code.

Other files that state a moved fact: none.
Files that link to the page: none. README.md and docs/marketplace.md do not mention it.
Gaps: none.
The page is deleted because no kept claim remained. The only files changed are stock/format.py and the deleted page.

I removed docs/stock-feed.md. Nothing on it needed to stay a document. I checked each of its four claims against the code:

- **No-stock SKUs are left out:** `stock_rows()` already shows this in its filter, its docstring and a test, so I dropped it.
- **Tab-separated lines (SKU, quantity, price):** `feed_line()` and its docstring already show this, so I dropped it.
- **Quantity cap of 9999:** `min(qty, MAX_FEED_QTY)` shows the cap, but not the reason for it. I added a comment above `MAX_FEED_QTY` in `stock/format.py`: the marketplace's quantity column is four digits wide and it rejects the whole file if a value is longer (MKT-204). That was the only fact worth moving.
- **`stock_rows()` must return rows sorted by SKU:** I did not carry this over because the code contradicts it. `write_feed()` calls `sorted()` on both `rows` and `prices` before the merge pass, so out-of-order input is not skipped. The page is stale on this point. `stock_rows()` also sorts its own output, so the requirement was doubly unnecessary. The `write_feed` docstring (merge pass, SKUs missing from either side are passed over) is accurate.

No other file linked to the page. I changed no code, only added the comment, and I created no new files.

I removed `docs/stock-feed.md` and moved what it said next to the code. Nothing on the page needed to stay a document. The tests still pass, and I changed no code.

- **Quantity cap:** `stock/format.py` now has a comment on `MAX_FEED_QTY`. It says the marketplace feed format has a four-digit quantity column and rejects the whole file if any value is longer (MKT-204).
- **Sort order:** the page said `stock_rows()` must return rows sorted by SKU. That is no longer true, because `write_feed()` sorts both `rows` and `prices` itself before its merge pass. I did not copy the claim. The `write_feed()` docstring in `stock/feed.py` now says the merge needs both sides in SKU order, so it sorts them and callers need not pre-sort.
- **Already covered:** the zero-stock exclusion and the tab-separated line format were already in the `stock_rows()` and `feed_line()` docstrings, so I added nothing for them.
- **Other docs:** `docs/marketplace.md` is about the SFTP pickup and the support contact, not this page, so I left it. Nothing else linked to the deleted page.

The `sorted(...)` in `stock_rows()` is now redundant, since `write_feed()` sorts anyway. I left it alone because you asked for comment changes only. You can drop it if you want.

I removed docs/stock-feed.md and moved its content next to the code.

- `stock/format.py`: a comment on `MAX_FEED_QTY` now records why it is 9999. The marketplace feed has a four-digit quantity column and rejects the whole file if any value is longer (MKT-204).
- `stock/feed.py`: a comment in `write_feed()` says it sorts both inputs itself, because the single merge pass silently skips out-of-order rows.
- The other doc bullets were already in the code: the empty-stock rule in the `stock_rows()` docstring, and the tab-separated line format in the `feed_line()` docstring. I did not repeat them.

The page's claim that `stock_rows()` must return rows sorted by SKU was out of date, so I did not carry it over. `write_feed()` sorts both lists itself, so callers do not need to pre-sort. The page's wording was wrong, not the code.

I left docs/marketplace.md alone. It describes the SFTP pickup time and the support contact, which are not about the code, so they still belong in a document.

I did not run the tests. The only code edits are comments.

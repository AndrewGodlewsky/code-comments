I removed `docs/stock-feed.md`. Nothing on it needed to stay a document, and nothing else linked to it. I haven't run the tests.

What moved into the code:
- **Quantity cap:** a comment above `MAX_FEED_QTY` in `stock/format.py` now gives the reason. The marketplace's quantity column is four digits wide and rejects the whole file if a value is longer (MKT-204).
- **Empty stock:** the `stock_rows()` docstring in `stock/rows.py` now says SKUs with no stock are left out.
- **Tab-separated lines:** `feed_line()` already says this in its docstring, so I added nothing.

What I did not carry over: the page said `stock_rows()` must return rows sorted by SKU, because `write_feed()` merges the rows with the price list and silently skips out-of-order rows. That is out of date. `write_feed()` now sorts both the rows and the prices itself, so it doesn't depend on the order of its input. Copying the claim into a comment would have been misleading. The `stock_rows()` docstring now says its output is sorted but that `write_feed()` doesn't rely on it.

`docs/marketplace.md` stays, since the 04:00 UTC pickup time and the seller support contact aren't code-level facts.

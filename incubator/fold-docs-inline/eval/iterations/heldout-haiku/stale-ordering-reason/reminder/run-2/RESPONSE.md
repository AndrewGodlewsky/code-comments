I moved the one fact from docs/stock-feed.md that the code does not show into a comment, and removed the page. Nothing left on it needed to stay a document.

What I did:

- Added a comment above `MAX_FEED_QTY` in `stock/format.py` recording why quantities are capped at 9999: the marketplace's feed format has a four-digit quantity column and rejects the whole file if any value is longer (MKT-204).
- Deleted `docs/stock-feed.md`. Neither `README.md` nor `docs/marketplace.md` links to it.
- No code was changed beyond that comment, and no files were created other than this message.

What I left off the page, and why:

- "`stock_rows()` leaves out SKUs that have no stock": the `qty > 0` filter in `stock/rows.py` shows this, and a test covers it.
- "Each feed line is tab-separated: SKU, quantity and price": the `feed_line` function and its docstring show this.

What I did not carry over because the code contradicts it:

- "`stock_rows()` must return rows sorted by SKU ... a row that arrives out of order is silently skipped." This is not true of the current code. `write_feed()` calls `sorted(rows)` and `sorted(prices)` itself before its merge pass, so out-of-order input is not skipped. `stock_rows()` does still return sorted output, which the code shows, so I did not add a comment about the ordering requirement. You may want to look at whether the sort in `stock_rows()` is still needed, or whether its docstring should say why it sorts.

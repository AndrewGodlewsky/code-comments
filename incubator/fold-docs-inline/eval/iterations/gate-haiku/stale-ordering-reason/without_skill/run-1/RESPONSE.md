I moved the stock feed notes into the code and removed docs/stock-feed.md. Nothing on the page needed to stay a document. No other file linked to it.

What changed:

- `stock/rows.py`: the `stock_rows()` docstring now says the rows are sorted by SKU and that SKUs with no stock are left out.
- `stock/format.py`: a comment above `MAX_FEED_QTY` explains the four-digit quantity column and the whole-file rejection (MKT-204). The tab-separated format was already documented in the `feed_line()` docstring.
- `stock/feed.py`: the `write_feed()` docstring now says rows may arrive in any order, because each price is looked up separately.

One note was wrong and I did not carry it over. The old page said `write_feed()` does a single merge pass and silently skips rows that arrive out of order. That is not true: `write_feed()` looks up each SKU's price in a dict. I ran it with unsorted rows (`B`, then `A`) and both lines were written.

`stock_rows()` still returns sorted rows, so the output order is unchanged. Nothing in this repo depends on that order any more. If the marketplace itself requires sorted SKUs, that requirement is not documented anywhere in the repo, so someone should confirm it with them before anyone relies on or removes the sort.

The existing tests pass (3 tests). I did not add a test for the sort order.

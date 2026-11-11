I moved the content of docs/stock-feed.md into the code and deleted the page. Nothing on it needed to stay a document.

- The quantity cap and its reason (the marketplace's four-digit quantity column, and the whole file being rejected otherwise, MKT-204) now sit above `MAX_FEED_QTY` in `stock/format.py`.
- The tab-separated line format was already documented on `feed_line`, so nothing was added.
- Leaving out SKUs with no stock is already stated by the `stock_rows` docstring, so nothing was added there beyond the sort contract below.
- The sort requirement is different. The old page said `stock_rows()` must return rows sorted by SKU because `write_feed()` needs that for its merge pass. That is no longer true of `stock_rows()`: `write_feed()` now sorts both `rows` and `prices` itself. The merge-pass constraint is still real inside `write_feed()`, so I recorded it there, with a comment saying both inputs are sorted in that function. I did not keep the claim that callers must sort.
- `stock_rows()` still returns sorted output, and `test_rows_skip_empty_stock` checks that. I added "sorted by SKU" to its docstring as the return contract.

Open question: the page gave no reason for `stock_rows()` sorting now that `write_feed()` sorts on its own. I did not invent one. If you know why it sorts, that reason belongs beside the sort in `stock/rows.py`. Otherwise it may be removable, but I have not changed it.

No code behaviour changed. The three unit tests pass (`python -I -m unittest discover -s tests -t .`). `docs/marketplace.md` is unchanged, and nothing else in the repository referred to `docs/stock-feed.md`.

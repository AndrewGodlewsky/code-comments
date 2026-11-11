I deleted `docs/stock-feed.md`. Nothing on it needed to stay a document. I checked each of its four points against the code:

- **Quantity cap (MKT-204)**: moved into `stock/format.py` as a comment above `MAX_FEED_QTY`. It states the four-digit column and the whole-file rejection, and keeps the MKT-204 pointer.
- **Rows must be sorted by SKU**: dropped as stale. `write_feed` already sorts both `rows` and `prices` before its merge pass, so an unsorted row is no longer skipped. I updated the `write_feed` docstring to say the inputs may arrive in any order and are sorted internally.
- **Tab-separated format**: dropped. The `feed_line` docstring already states it.
- **SKUs with no stock are left out**: dropped. The `stock_rows` docstring and the `qty > 0` filter already cover it.

Two things for you to decide, which I did not change:

- `stock_rows` still returns sorted output. `write_feed` no longer needs that, so the sort is redundant unless you want it kept as a contract for other callers.
- No test covers `write_feed` with unsorted input. Adding one would pin the new docstring claim.

`docs/marketplace.md` is untouched, and no other file refers to `stock-feed.md`. The 3 existing unit tests pass. I made no git commits, because this exercise forbids git.

I removed `docs/stock-feed.md` and moved its content into the code next to the behaviour it describes. Tests pass (3 of 3).

What went where:

- **Quantity cap (MKT-204):** the reason for `MAX_FEED_QTY` is now a comment above the constant in `stock/format.py`. The marketplace rejects the whole file if a quantity is longer than four digits.
- **Leaving out SKUs with no stock:** `stock_rows()` in `stock/rows.py` already filters them, and its docstring now says so.
- **Sorted rows:** `stock_rows()` returns rows sorted by SKU, and its docstring says so.
- **Tab-separated lines:** already documented in the `feed_line()` docstring in `stock/format.py`, so nothing new was needed.

One claim did not survive the move. The page said callers must pass rows sorted by SKU, because an out-of-order row is "silently skipped". `write_feed()` in `stock/feed.py` now sorts both `rows` and `prices` itself, so input order no longer matters. I updated its docstring to say so and left the code alone. `stock_rows()` still sorts too, which is now redundant for `write_feed()` but harmless. I did not change behaviour or add a test for unsorted input; that would be a separate change if you want it.

`docs/marketplace.md` is unchanged. Nothing else in the repo linked to `docs/stock-feed.md`.

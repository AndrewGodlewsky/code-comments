I removed `docs/stock-feed.md` and moved what belonged in it next to the code:

- **Quantity cap and MKT-204:** the reason `MAX_FEED_QTY` exists (the marketplace's four-digit quantity column rejects the whole file otherwise) now sits as a comment above the constant in `stock/format.py`.
- **Tab-separated line format:** already documented in the `feed_line()` docstring, so nothing was added.
- **Skipping SKUs with no stock:** `stock_rows()` in `stock/rows.py` now says in its docstring that it leaves those out and returns rows sorted by SKU.
- **Sort-order requirement:** dropped. The page said `write_feed()` silently skips out-of-order rows, but `write_feed()` already sorts both `rows` and `prices` before its merge pass, so order does not matter. I updated its docstring to say inputs may arrive in any order.

`docs/marketplace.md` stays as it is, since it covers the external collection schedule and the seller support contact, not code. Nothing in the repo referenced `docs/stock-feed.md`. The three existing tests pass.

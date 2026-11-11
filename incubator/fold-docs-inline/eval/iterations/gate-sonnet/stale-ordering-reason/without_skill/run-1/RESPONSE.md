I removed `docs/stock-feed.md`. Nothing on it needed to stay a document.

What moved, and what didn't:

- **Quantity cap (MKT-204):** this was the only fact not already in the code. It is now a comment on `MAX_FEED_QTY` in `stock/format.py`. It says the feed's quantity column is four digits wide and the marketplace rejects the whole file if any value is longer.
- **Tab-separated lines, and leaving out SKUs with no stock:** the docstrings on `feed_line()` and `stock_rows()` already say this, and the tests cover it. I added nothing.
- **"Rows must be sorted by SKU":** I deliberately did not carry this over. The page said `write_feed()` does a single merge pass over the rows and the price list, and silently skips out-of-order rows. That is no longer true. `write_feed()` looks each SKU up in the `prices` dict, so order doesn't affect the output. Copying the claim into a comment would have documented a constraint that doesn't exist. `stock_rows()` still returns sorted rows, which is harmless. If you want a stable feed order, say so and I'll add a comment for that. Otherwise you could drop the `sorted()`.

I left `README.md` and `docs/marketplace.md` alone. Neither linked to the removed page.

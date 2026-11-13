I removed docs/stock-feed.md. Nothing on it needed to stay a document.

What I did with each point:

- **Empty stock is left out.** Already covered by the `stock_rows` docstring and `test_rows_skip_empty_stock`, so I added nothing.
- **Rows must be sorted for the merge pass.** I dropped this one. `write_feed` now sorts both `rows` and `prices` itself, so a caller's order no longer matters and the "silently skipped" risk is gone. Recording it would have stated a false rule. `stock_rows` still returns sorted output; that sort is now redundant but I left the code alone.
- **Tab-separated line format.** Already in the `feed_line` docstring.
- **Quantity cap.** Moved to a comment above `MAX_FEED_QTY` in `stock/format.py`. It gives the reason (four-digit marketplace column, whole file rejected, MKT-204) and says that `feed_line()` applies the cap.

No other file referenced docs/stock-feed.md. docs/marketplace.md is unchanged. I did not use git, so nothing is committed.

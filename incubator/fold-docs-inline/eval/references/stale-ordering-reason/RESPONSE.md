docs/stock-feed.md is deleted. Claim by claim:

- **`stock_rows()` leaves out SKUs with no stock.** Dropped: the `qty > 0` filter shows it.
- **`stock_rows()` must sort by SKU because `write_feed()` merge-joins rows with the price list, and skips a row that arrives out of order.** Not moved: it's out of date. `write_feed()` in stock/feed.py does still walk the rows and the price list in one merge pass, but it sorts both itself first (`sorted(rows)`, `sorted(prices)`), so rows in any order are all written and none is skipped. Nothing else I found depends on the sort in `stock_rows()`, and nothing says why it is there, so I left it uncommented rather than guess. If you know a reason, tell me and I'll add it.
- **Each feed line is tab-separated: SKU, quantity and price.** Dropped: `feed_line()` and its docstring show it.
- **Quantities are capped at 9999 because the feed's quantity column is four digits (MKT-204).** Moved to a comment above `MAX_FEED_QTY` in stock/format.py.

docs/marketplace.md is untouched. No code changed and no files were added.

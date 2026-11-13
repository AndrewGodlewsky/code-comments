I checked each claim on docs/stock-feed.md against the code and removed the page.

What moved into code:
- The quantity cap rationale (four-digit quantity column, whole file rejected if a value is longer, MKT-204) is now a comment above `MAX_FEED_QTY` in `stock/format.py`. The cap itself was already in the code.

What I left out because the code already shows it:
- `stock_rows()` leaves out SKUs with no stock (`qty > 0` in `stock/rows.py`, covered by `test_rows_skip_empty_stock`).
- Feed lines are tab-separated SKU, quantity and price (`feed_line` in `stock/format.py`).
- `write_feed()` walks rows and prices in one merge pass and skips a SKU missing from either side (its docstring says so).

What I did not carry over because the code contradicts it:
- The page says `stock_rows()` must return rows sorted by SKU, and that an out-of-order row is silently skipped. This is wrong. `write_feed()` in `stock/feed.py` sorts `rows` itself (`sorted(rows)`) before the merge pass, so it does not depend on the order `stock_rows()` returns. `stock_rows()` does still sort its output, but no caller needs that. Nothing was moved for this claim.

What I could not verify:
- The MKT-204 reference and the marketplace's rejection behaviour are not visible in the code. I carried them over as written in the comment, and they should be checked against the ticket.

Other changes:
- Deleted `docs/stock-feed.md`. Nothing on it needed to stay a document.
- `README.md` and `docs/marketplace.md` do not link to the deleted page, so no links needed fixing. `docs/marketplace.md` is unchanged.
- No other code changed and no new files were created. I did not run the tests.

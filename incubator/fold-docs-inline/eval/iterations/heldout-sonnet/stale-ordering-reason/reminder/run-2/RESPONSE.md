I removed docs/stock-feed.md. Nothing on it needed to stay a document, and I changed no code.

I checked each claim against the code:

- **Zero-stock SKUs are left out.** I did not carry this over. `stock_rows()` in `stock/rows.py` filters on `qty > 0`, and `test_rows_skip_empty_stock` covers it.
- **Rows must be sorted by SKU or they are silently skipped.** I did not carry this over, because the code contradicts it. `write_feed()` in `stock/feed.py` sorts both `rows` and `prices` itself before the merge pass, so out-of-order input is not skipped. The page is stale here, and the `write_feed` docstring already describes the merge pass. If you want sorted input to be a rule, that would be a code change.
- **Lines are tab-separated: SKU, quantity, price.** I did not carry this over. `feed_line()` and its docstring show it.
- **Quantities are capped at 9999 because the feed has a four-digit column and rejects the whole file (MKT-204).** I moved this into a comment above `MAX_FEED_QTY` in `stock/format.py`. The cap is visible in the code, but the reason and the ticket are not.

No other file linked to the page. `docs/marketplace.md` is about the SFTP drop and the support contact. It has no code to sit beside, so I left it as it is.

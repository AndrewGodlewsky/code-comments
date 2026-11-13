# Stock feed

- `stock_rows()` leaves out SKUs that have no stock.
- `stock_rows()` must return rows sorted by SKU: `write_feed()` walks the rows and the
  price list together in a single merge pass, and a row that arrives out of order is
  silently skipped.
- Each feed line is tab-separated: SKU, quantity and price.
- Quantities are capped at `MAX_FEED_QTY` (9999) because the marketplace's feed format
  has a four-digit quantity column and rejects the whole file if any value is longer
  (MKT-204).

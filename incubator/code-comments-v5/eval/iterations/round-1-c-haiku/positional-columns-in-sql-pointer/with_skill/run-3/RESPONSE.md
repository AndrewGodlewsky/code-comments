The nightly CSV export now has a `currency` column directly after `amount`. The header order is `id, account, amount, currency, ts`. The change is in `exporter/csv_out.py` (`COLUMNS`), and I added a test that checks currency sits beside amount and carries the entry's code (`EUR` in the test). All 7 tests pass.

The warehouse load reads the CSV by position, not by header name. `deploy/warehouse/load_ledger.sql` selected `c1..c4` into `ledger_raw`, so with currency at position 4, `ts` would have landed in `posted_at`'s neighbour and every later field would shift. I changed the load to `SELECT c1, c2, c3, c5`, which skips the currency field and keeps `posted_at` reading `ts`. I also rewrote that file's comment, which said new columns must go at the end; that is no longer true, and the comment now describes the current mapping. `ledger_raw` has no currency column, so the currency value is not stored in the warehouse. I did not change the table, because that was not asked. If finance needs currency in the warehouse, that needs a new column on `ledger_raw` (added at the end, per `deploy/warehouse/schema.sql`) and a matching change to the load.

Things to check before the next nightly run:
- The loader change must ship with the CSV change. Deploying the exporter alone would load `ts` into the wrong field.
- `reports/monthly.py` and `docs/finance.md` need no change, because monthly totals read by header name and the finance doc says columns are found by name.
- I could not run the warehouse load here, so the SQL is checked by reading only.

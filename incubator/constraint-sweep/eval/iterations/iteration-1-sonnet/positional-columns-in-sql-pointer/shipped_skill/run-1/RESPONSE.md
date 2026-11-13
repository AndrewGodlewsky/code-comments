I added `currency` to the CSV export, but as the last column (after `ts`), not next to `amount`.

The warehouse load (`deploy/warehouse/load_ledger.sql`) reads the CSV fields by position (c1..c4) and skips the header row. Inserting currency beside amount would shift `ts` to c5, and the nightly load would put the currency code into `posted_at`. Finance finds columns by header name, so the order doesn't affect them.

Changes:
- `exporter/csv_out.py`: `currency` appended to `COLUMNS`. The comment now says new columns go at the end.
- `tests/test_csv_out.py`: header check includes `currency`, plus a test for the value.
- `deploy/warehouse/load_ledger.sql`: comment notes that c5 (currency) is not loaded, because `ledger_raw` has no column for it.

Tests pass. The warehouse still does not receive currency. Loading it needs a new `ledger_raw` column (added at the end) and `c5` in the load query. I can do that if you want.

If you still want amount and currency side by side, that is possible. It means changing the load query to read ts from c5, and deploying it together with the export change. Tell me if you want that.

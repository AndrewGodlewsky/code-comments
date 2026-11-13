I added `currency` to the CSV export, but as the last column, not next to `amount`.

The nightly warehouse load (`deploy/warehouse/load_ledger.sql`) reads CSV fields by position (c1 to c4) and skips the header row. Putting `currency` between `amount` and `ts` would have loaded the timestamp into the wrong column in `ledger_raw` (and the currency into `posted_at`). Finance finds columns by header name, so the position makes no difference to them. In a spreadsheet, `currency` will sit at the far right, not next to `amount`.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `id, account, amount, ts, currency`. I added a comment saying new columns must be appended because the warehouse load is positional.
- `tests/test_csv_out.py`: tests that `currency` is written, and that the first four columns stay in their old positions.

The unit tests pass. The warehouse load itself was not run. It still loads only the first four fields, so `currency` is not stored in the warehouse yet. That needs a separate change: a new `ledger_raw` column plus an edit to `load_ledger.sql`. Tell me if you want it.

If finance really wants `currency` right beside `amount` in the file, the load SQL and schema would have to change in step with the export. That is a bigger change.

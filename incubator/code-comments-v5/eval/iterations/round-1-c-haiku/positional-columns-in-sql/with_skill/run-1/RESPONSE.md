I added `currency` to the CSV export, but as the last column, not next to `amount`.

Column order is now `id, account, amount, ts, currency`.

Why not beside `amount`: `deploy/warehouse/load_ledger.sql` stages each file as `export_staging(c1, c2, ...)` and reads fields by position (`SELECT c1, c2, c3, c4`). It skips the header row. If `currency` went between `amount` and `ts`, `ts` would land in `c4`, and `posted_at` would receive currency codes instead of timestamps every night. Finance finds columns by header name, so appending costs them nothing.

Changes:
- `exporter/csv_out.py`: `COLUMNS` now includes `currency` at the end. I added a comment above it stating that the warehouse loader reads by position, so new columns must go at the end.
- `tests/test_csv_out.py`: the header test checks for `currency`, and a new test checks that `currency` is written as given (`EUR`).

Tests: `python -m unittest discover -s tests -t .` runs 7 tests, all passing.

Not changed, and worth a decision: `load_ledger.sql` still maps only four fields and does not load currency into `ledger_raw`, and `schema.sql` has no currency column. Finance may expect currency in the warehouse too. If so, that is a follow-up: add a `currency` column at the end of `ledger_raw` and map `c5` in the load. I did not make that change because the request was only for the CSV export.

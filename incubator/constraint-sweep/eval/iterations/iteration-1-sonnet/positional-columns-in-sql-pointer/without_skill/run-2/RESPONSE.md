The CSV export now has a `currency` column (ISO 4217 code, e.g. `EUR`), but I put it at the end of the row, not next to `amount`.

Why: the nightly warehouse load (`deploy/warehouse/load_ledger.sql`) skips the header and reads fields by position (`c1`..`c4`). Putting currency between `amount` and `ts` would make `ts` load into the wrong column there, and the load would still run without any error. Finance finds columns by header name, so they will see the same thing wherever the column sits.

If you do want it beside `amount`, the load SQL and `ledger_raw` need to change in the same release. I did not do that. The table only ever gets columns added at the end, and a mid-table change needs a migration.

Changes:
- `exporter/csv_out.py`: `currency` added to the end of `COLUMNS`; the comment now says new columns go at the end.
- `tests/test_csv_out.py`: tests for the currency value and for the first four columns keeping their positions.
- `docs/finance.md`: one line describing the new column.

Not done: the warehouse does not load `currency` yet. That needs a `ledger_raw` column added and `load_ledger.sql` updated to select `c5`. Say if you want it.

Tests pass.

The nightly CSV now has a `currency` column directly after `amount`. The column order is id, account, amount, currency, ts.

The warehouse loader in `warehouse/load.sql` reads the export by position, so I changed it to match. It now reads `posted_at` from the fifth field (`c5`) and skips currency (`c4`). Without that change, `ts` would have landed in the `posted_at` slot and every later field would have shifted. The warehouse load output is unchanged.

Currency is in the export but not in the warehouse. `ledger_raw` has no currency column, so the loader does not store it. If finance needs it in the warehouse, that needs a new column added at the end of `ledger_raw` and a matching line in `load.sql`. I have not made that change.

Changes:
- `exporter/csv_out.py`: `COLUMNS` now includes `currency` after `amount`.
- `warehouse/load.sql`: maps `c1, c2, c3, c5` and the comment explains the skipped column.
- `tests/test_csv_out.py`: added a test that `currency` sits right after `amount` and holds the entry's value.

All 6 unit tests pass.

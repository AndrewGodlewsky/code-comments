The nightly CSV now has a `currency` column directly after `amount`. The header is `id,account,amount,currency,ts`, and the currency code is written for each row.

One change outside the exporter was needed. `deploy/warehouse/load_ledger.sql` loads the file by column position (`c1`..`c4`), and its comment said new columns must go at the end. Adding currency in the middle would have shifted `ts` into the `posted_at` slot, so I updated the loader's SELECT to read `c1, c2, c3, c5` and left currency out of the warehouse load, since `ledger_raw` has no currency column. The comment now lists the positions.

Changes:
- `exporter/csv_out.py`: `COLUMNS` now includes `currency` after `amount`.
- `deploy/warehouse/load_ledger.sql`: SELECT reads `c5` for `posted_at`; comment updated.
- `tests/test_csv_out.py`: added a test that `currency` sits right after `amount` and holds the entry's code.

Checks: the unit tests pass (7 tests), and a sample export produces the expected header and row.

Before deploying: the loader change and the exporter change must go out together. Files already in the warehouse keep their old layout, and the loader expects the new five-field layout from tonight's run onward. If finance wants currency in the warehouse table, that needs a new column added at the end of `ledger_raw` plus a loader update; I did not make that change.

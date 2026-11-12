I added `currency` to the nightly CSV export, but as the last column, not directly after `amount`. Header order is now `id, account, amount, ts, currency`.

Why not next to amount: `deploy/warehouse/load_ledger.sql` loads the CSV by position (`c1..c4` into `ledger_raw`). Putting currency after amount would shift `ts` into `c5`, so the 01:30 nightly `warehouse-load` would write the currency code into `posted_at` and the timestamp would be dropped. Your note said the order is up to us because finance finds columns by header name, so appending at the end gives finance the new column without breaking the load.

Changes:
- `exporter/csv_out.py`: `COLUMNS` gets `"currency"` at the end. I added a short comment above it stating that the warehouse loader reads by position, so new columns go at the end, and pointing to `deploy/warehouse/load_ledger.sql`.
- `tests/test_csv_out.py`: the header test also checks for `currency`, and a new test checks that the currency value is written as given (`EUR` for the test entry).

Verification: `python -m unittest discover -s tests -t .` runs 7 tests, all passing.

Needs your decision:
- If finance really needs currency physically beside amount, the warehouse loader and `deploy/warehouse/schema.sql` must change first (the loader mapping and the table, which currently only grows at the end). I did not change either, because that is production load behaviour and outside this request.
- `deploy/warehouse/load_ledger.sql` does not map currency, so it lands in the staging table but not in `ledger_raw`. If the warehouse should store currency, that is a separate change, and it needs a column added to `schema.sql` as well.

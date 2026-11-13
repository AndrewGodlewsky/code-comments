I added `currency` to the nightly CSV export, but as the last column, not directly after `amount`.

The header order is not up to us. `deploy/warehouse/load_ledger.sql` stages the file as `export_staging(c1, c2, ...)` and selects `c1` to `c4` by position, and it skips the header row. Putting `currency` between `amount` and `ts` would move `ts` to position 5 and load the currency code into the `posted_at` column. The file's own comment says new export columns go at the end for this reason. Finance finds columns by header name, so appending `currency` meets their need.

Changes, all in this repository:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`. I extended the comment above it to say new columns go at the end and to point to `load_ledger.sql`.
- `tests/test_csv_out.py`: the header test also checks for `currency`, and a new test checks that `currency` is the last header and carries `EUR` for the sample entry.

The unit tests pass (7 tests, run with `python -m unittest discover -s tests -t .`).

Not done, and needs a decision from you:
- The warehouse does not load `currency` yet. `deploy/warehouse/schema.sql` has no currency column and `load_ledger.sql` selects only `c1` to `c4`. Adding it means a `currency` column on `ledger_raw` (at the end, per the schema note) and a `c5` in the load select. I left both alone because you did not ask for warehouse changes.
- If you do want `currency` directly after `amount` in the CSV, `load_ledger.sql` must be updated in the same change, and the warehouse load must be checked before the next nightly run at 01:30.

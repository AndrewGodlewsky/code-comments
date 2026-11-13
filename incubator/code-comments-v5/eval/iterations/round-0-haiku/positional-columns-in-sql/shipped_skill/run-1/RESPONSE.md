I added `currency` to the nightly CSV export, but at the end of the row, not next to `amount`. The header is now `id, account, amount, ts, currency`.

I did not place it beside `amount` because the warehouse load reads the CSV by position. `deploy/warehouse/load_ledger.sql` stages each field as `c1..c4` and maps them to `entry_id, account_code, amount, posted_at`. With `currency` between `amount` and `ts`, the 01:30 `warehouse-load` would write the currency code into `posted_at` and drop the timestamp. The SQL file's own comment says new export columns must go at the end for this reason. Finance finds columns by header name, so end placement meets their need.

Changes:
- `exporter/csv_out.py`: `currency` added to `COLUMNS` after `ts`. I added a comment above `COLUMNS` recording that the warehouse load reads by position and new columns go at the end.
- `tests/test_csv_out.py`: the header test now also checks for `currency`, and a new test checks that the value is written as `EUR`.

The 7 unit tests pass (`python -m unittest discover -s tests -t .`). I did not run the warehouse load.

If you want `currency` directly beside `amount`, the warehouse side needs changing first. `deploy/warehouse/load_ledger.sql` would need a `currency` field mapped to a new column, and `deploy/warehouse/schema.sql` would need that column added to `ledger_raw`. Both are production-facing, so I left them alone.

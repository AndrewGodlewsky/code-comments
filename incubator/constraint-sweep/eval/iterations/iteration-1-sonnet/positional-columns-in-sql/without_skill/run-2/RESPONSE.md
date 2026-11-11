The CSV export now has a `currency` column, but I put it at the end of the row (after `ts`), not next to `amount`.

Finance finds columns by header name, so for them the position makes no difference. The nightly warehouse load (`deploy/warehouse/load_ledger.sql`) does not use header names. It reads fields by position (`c1`..`c4`). Putting currency beside amount would have moved `ts` into the fifth slot. Every night's `posted_at` would then have loaded the wrong value, with no error. Adding the column at the end leaves that load working as it is.

Changes:
- `exporter/csv_out.py`: added `currency` to `COLUMNS`, with a comment saying why it goes last.
- `tests/test_csv_out.py`: the header test now checks for `currency`. I added a test that the currency value is written, and a test that the first four columns stay where they were.

The existing tests and the new ones pass.

The warehouse still ignores the new column. If you want currency in `ledger_raw`, that is a separate change. It needs `ALTER TABLE ledger_raw ADD COLUMN currency` in `schema.sql` and a matching update to `load_ledger.sql`. Tell me if you want me to do that.

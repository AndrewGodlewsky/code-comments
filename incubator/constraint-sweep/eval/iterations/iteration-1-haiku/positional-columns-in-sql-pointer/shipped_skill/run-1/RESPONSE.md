I added `currency` to the nightly CSV export, but as the last column (after `ts`), not next to `amount`.

The reason: `deploy/warehouse/load_ledger.sql` loads the file by position (`SELECT c1, c2, c3, c4 FROM export_staging`), and the comment in `exporter/csv_out.py` and in that SQL file says new columns must go at the end. Putting `currency` between `amount` and `ts` would make it position 4, so the nightly load would write currency into `posted_at` and drop timestamps entirely. Appending keeps the existing four positions unchanged.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`.
- `tests/test_csv_out.py`: the header test checks for `currency`, a new test checks that `id, account, amount, ts` keep their positions, and a new test checks that `currency` is written as `EUR`.

All 8 unit tests pass.

Decision for you: if finance really needs `currency` beside `amount`, the warehouse side has to change first. `load_ledger.sql` would need to map fields by header name or use the new position, and `deploy/warehouse/schema.sql` would need a `currency` column added at the end of `ledger_raw`. I did not touch the warehouse files, since they are production load code. Tell me which way you want to go.

I did not commit, since the task said not to use git.

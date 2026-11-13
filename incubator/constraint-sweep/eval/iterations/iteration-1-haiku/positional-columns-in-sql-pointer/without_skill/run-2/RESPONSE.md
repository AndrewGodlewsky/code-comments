I added the currency code to the nightly CSV export as a new `currency` column, but it is the last column, not next to `amount`.

The reason is the warehouse load. `deploy/warehouse/load_ledger.sql` stages each CSV by position (`c1`..`c4` map to `entry_id`, `account_code`, `amount`, `posted_at`). If `currency` went between `amount` and `ts`, `ts` would load into the `posted_at` column's position as `currency` and every timestamp would be wrong. The comment in that file says new export columns must go at the end, so I followed it.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`, with a comment saying new columns go at the end.
- `tests/test_csv_out.py`: a new test checks the exact header and that the currency value is `EUR`.

The existing tests pass (7 tests, `python -m unittest`). I did not run the warehouse load or the cron jobs.

Finance finds columns by header name, and `docs/finance.md` says order does not matter to them, so the end position should not affect them.

If finance really needs `currency` beside `amount`, that is a coordinated change. It means updating `load_ledger.sql` to read the new positions, adding a `currency` column to `ledger_raw` with `ALTER TABLE ... ADD COLUMN`, and deploying both before the next nightly run. I did not make that change, because it touches the production load.

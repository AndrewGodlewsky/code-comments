I added `currency` to the CSV export, but as the last column (after `ts`), not directly beside `amount`. Please read the reason before we merge.

The nightly warehouse load, `deploy/warehouse/load_ledger.sql`, reads the export by position: it maps `c1` to `entry_id`, `c2` to `account_code`, `c3` to `amount` and `c4` to `posted_at`. It skips the header row, so it never checks names. If `currency` went between `amount` and `ts`, `c4` would load the currency code into `posted_at` and the timestamps would be dropped, with no error. The loader's own comment says new export columns go at the end for this reason.

What changed:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`, with a comment that new columns are appended only.
- `tests/test_csv_out.py`: two new tests. One checks that the `currency` value is written under its header. The other pins the first four header names and their order, so a later reorder fails the build.
- `docs/finance.md`: a short note that `currency` is the last column and gives the currency of `amount` on the same row.

Finance finds columns by header name, so the position at the end works for them.

If the side-by-side layout is still wanted, it needs a coordinated change, not just a reorder in the exporter:
1. Update `load_ledger.sql` to map the new positions.
2. Add a `currency` column to `ledger_raw` in `schema.sql`, which only accepts additions at the end, so that change would need its own migration.
3. Ship the exporter and loader changes together, before the next 01:30 run in `deploy/crontab`.

I did not make those warehouse changes, since they touch production load and schema.

Tests: `python -m unittest discover -s tests -t .` runs 8 tests, all passing.

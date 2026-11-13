The nightly CSV export now has a `currency` column, but it is the last column, not next to `amount`.

What changed:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`.
- `tests/test_csv_out.py`: the header test includes `currency`, and two new tests check that `currency` is the last header and that each row carries the entry's currency (`EUR` in the fixture).
- `python -m unittest discover -s tests -t .` passes (8 tests).

Why not beside `amount`:
`deploy/warehouse/load_ledger.sql` loads the file by position. It stages each row as `c1..cN` and selects `c1, c2, c3, c4` into `ledger_raw`. Its comment says new export columns must go at the end, because a column inserted earlier shifts every later field into the wrong warehouse column. Putting `currency` after `amount` would make `currency` land in `c4`, and the nightly load would write currency codes into `posted_at` and drop the timestamps, without any error. Appending keeps the existing load correct, because the loader ignores `c5`.

Other constraints found by grepping the whole repository:
- `deploy/warehouse/schema.sql` says columns are only ever added at the end. `ledger_raw` has no currency column, so the warehouse load drops `currency` for now.
- `docs/finance.md` and the comment in `reports/monthly.py` say finance and the reader find columns by header name, so the order does not matter to them. This is why appending is safe for them.
- `reports/monthly.py` reads by header name, so the new column does not affect monthly totals.

If finance needs `currency` in the warehouse too, that is a coordinated change, not a CSV change. Add `currency` to `ledger_raw` with `ALTER TABLE ... ADD COLUMN` at the end, and add it to the `SELECT` in `load_ledger.sql` as `c5`. Do this before or with the exporter change. The loader does not need to reorder columns, because the export stays in append order. I have not made those warehouse changes. Moving `currency` beside `amount` would also require changing the staging contract in `load_ledger.sql`, which is a production change that needs your sign-off.

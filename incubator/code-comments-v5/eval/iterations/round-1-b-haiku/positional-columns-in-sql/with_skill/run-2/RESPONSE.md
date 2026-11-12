The nightly CSV now has a `currency` column directly after `amount`:

`id, account, amount, currency, ts`

One part of your premise was wrong. The order is not free: `deploy/warehouse/load_ledger.sql` stages the CSV by position (c1..c5) and maps c1-c4 into `ledger_raw`. With currency at position 4, the old SELECT would have loaded currency into `posted_at`, and `ts` would have been dropped. So I changed the load to `SELECT c1, c2, c3, c5`, which keeps the warehouse receiving the same four fields as before. The comment in that file now describes the position mapping instead of the old "append only" rule.

Other changes:
- `exporter/csv_out.py`: added `currency` to `COLUMNS`, with a comment that the warehouse loader depends on their order.
- `tests/test_csv_out.py`: the header test now checks for `currency`. New tests check that it sits right after `amount` and that its value is written as given. All 8 tests pass.
- `docs/finance.md`: one sentence says the `currency` column sits after `amount` and holds the ISO 4217 code.

Things to check before the next nightly run:
- The currency code is not loaded into the warehouse, because `ledger_raw` has no currency column. If finance needs it there, that means an `ALTER TABLE ... ADD COLUMN` plus a change to the load SELECT.
- I could not run `warehouse-load`, since it is not in this repository. Confirm that its `export_staging` accepts a five-field row; the loader's staging logic is outside what I could read.
- Anything outside this repo that reads the export by position will also break. Finance's header-based lookups and `reports/monthly.py` are not affected.
- I did not commit anything.

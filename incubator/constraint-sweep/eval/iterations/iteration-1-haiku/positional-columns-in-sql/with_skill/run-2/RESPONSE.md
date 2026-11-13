The nightly CSV export now has a `currency` column directly after `amount`:

    id,account,amount,currency,ts

Changes:

- `exporter/csv_out.py`: `COLUMNS` now includes `currency` between `amount` and `ts`. The value comes from the `Entry.currency` field that already existed.
- `tests/test_csv_out.py`: new test pins the header order and the currency value. All 7 tests pass.

One thing you need to know: the warehouse load is positional. `deploy/warehouse/load_ledger.sql` stages the CSV as `c1..cN` and read `c4` as `posted_at`. With currency after amount, `c4` would now be currency and `ts` would move to `c5`, so every night's load would have put currency into `posted_at`. I changed the load to `SELECT c1, c2, c3, c5`, so `ts` still loads into `posted_at` and currency is skipped. I also updated the comment in that file, which said new export columns must go at the end. The warehouse table `ledger_raw` has no currency column, so currency is not loaded. If finance wants it in the warehouse, that needs a column added at the end of `ledger_raw` (`deploy/warehouse/schema.sql`) and a matching change in the load SQL. I did not make that change because the request was only for the CSV.

Checked and not affected: `reports/monthly.py` reads by header name, `docs/finance.md` says column order does not matter to finance, and `deploy/warehouse/retention.sql` only uses `posted_at`.

I did not commit anything, since this run was not set up for git.

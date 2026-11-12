The nightly CSV export now has a `currency` column directly after `amount`:

`id,account,amount,currency,ts`

The change is in `exporter/csv_out.py` (`COLUMNS`). Finance finds columns by header name, so this does not affect the spreadsheet side.

One thing you need to know: the warehouse load reads the export by position, not by header. `deploy/warehouse/load_ledger.sql` stages each file as `c1, c2, ...` and selects `c1, c2, c3, c4` as `entry_id, account_code, amount, posted_at`. Inserting `currency` before `ts` moves `ts` to position 5, so without a fix `posted_at` would have loaded the currency code. Its comment also said new columns must go at the end. I kept the side-by-side placement you asked for and updated the load to match:

- `deploy/warehouse/load_ledger.sql` now selects `c1, c2, c3, c5`. Position 4 (currency) is not loaded, because `ledger_raw` has no currency column. The header comment now describes the current positions and says the SELECT must change whenever the column order does.
- `exporter/csv_out.py` comment now says the SELECT must be updated when `COLUMNS` changes.

Other consumers: `reports/monthly.py` reads by header name, so it is unaffected. `deploy/warehouse/schema.sql` is unchanged, since the warehouse does not store currency. If finance wants currency in the warehouse table, that needs a new column added at the end of `ledger_raw` and a matching change to the SELECT.

Changes:
- `exporter/csv_out.py`: `COLUMNS` order and comment.
- `deploy/warehouse/load_ledger.sql`: SELECT and comment.
- `tests/test_csv_out.py`: new test that `currency` sits right after `amount` with value `EUR`.
- `docs/finance.md`: one sentence noting the `currency` column.

Verification: `python -m unittest discover -s tests -t .` passes (7 tests). A sample export of one cleared record produced `id,account,amount,currency,ts` / `E-1,4000,12.50,EUR,2026-11-01T09:00:00Z`. I did not run `warehouse-load` against a real database, so the updated SELECT is checked by reading it, not by a load.

Not committed or pushed, because the instructions for this run said not to use git.

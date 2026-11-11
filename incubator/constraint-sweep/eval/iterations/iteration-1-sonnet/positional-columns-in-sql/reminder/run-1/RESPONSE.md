I added `currency` to the CSV export, but at the end of the row, not next to `amount`.

Finance finds columns by header name, so they would be fine with either placement. The warehouse load is the problem. `deploy/warehouse/load_ledger.sql` reads the file by position (`c1..c4`) and skips the header. It says new export columns must go at the end, otherwise every field after the new one loads into the wrong column. `schema.sql` also says columns are only ever added at the end. Putting currency beside amount would have loaded `ts` into `posted_at` incorrectly every night at 01:30.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `id, account, amount, ts, currency`. I added a comment there about the positional constraint.
- `tests/test_csv_out.py`: tests that currency is written and that the first four columns keep their positions. The unit tests pass.

I left these alone:
- `reports/monthly.py` reads by header name, so it is unaffected.
- The warehouse load ignores the new fifth field. Currency is in the CSV but not in `ledger_raw`. If you want it there, someone needs to run `ALTER TABLE ledger_raw ADD COLUMN currency` and add `c5` to `load_ledger.sql`. I did not do that because it changes production warehouse schema.
- If side by side matters to finance, the options are to change the warehouse load and schema together first, or to have finance reorder in their spreadsheet.

The CSV export now has a `currency` column (for example `EUR`). I put it last, not next to `amount`, because moving it would break the nightly warehouse load.

Why it is last: `deploy/warehouse/load_ledger.sql` reads the CSV by position (`c1..c4`) and skips the header row. Its comment says new export columns must go at the end. A column inserted after `amount` would shift `ts` into the wrong warehouse column. Finance finds columns by header name (`docs/finance.md`, `reports/monthly.py`), so the order does not matter to them, and the column order is now `id, account, amount, ts, currency`.

What changed:
- `exporter/csv_out.py`: added `currency` to the end of `COLUMNS` and updated the comment.
- `tests/test_csv_out.py`: the header test now checks for `currency`. I added a test that the currency value is written, and a test that the first four columns keep their positions.

The unit tests pass. I did not run the warehouse load itself.

The warehouse still loads only the first four fields, so `currency` will not reach `ledger_raw` yet. Adding it there means a `currency` column in `schema.sql` (`ALTER TABLE ... ADD COLUMN`) and `c5` in `load_ledger.sql`. I left that alone because it changes the warehouse table. Tell me if you want it.

If you really want `currency` beside `amount` in the file, the warehouse load has to change in the same release.

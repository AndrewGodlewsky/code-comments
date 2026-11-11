The CSV now has a `currency` column (e.g. `EUR`), but it is the last column, after `ts`, not right next to `amount`.

Why: `deploy/warehouse/load_ledger.sql` (the nightly warehouse load, run from `deploy/crontab`) reads the CSV by position (`c1..c4`) and skips the header. Its comment says new export columns must go at the end. Putting `currency` beside `amount` would shift `ts` into the wrong warehouse column. `schema.sql` also says columns are only added at the end. Finance finds columns by header name, so for them the position makes no difference.

Changes:
- `exporter/csv_out.py`: added `"currency"` at the end of `COLUMNS`, with a comment about the positional contract.
- `tests/test_csv_out.py`: added tests for the currency value and for the first four columns keeping their positions. All tests pass.

Not changed: the warehouse load and schema do not load `currency` yet. It is ignored there, which is safe. To store it, add a column to `ledger_raw` with `ALTER TABLE ... ADD COLUMN` and select `c5` in the load. Tell me if you want that. If you do want `currency` beside `amount` in the CSV, the load SQL would have to change in the same release.

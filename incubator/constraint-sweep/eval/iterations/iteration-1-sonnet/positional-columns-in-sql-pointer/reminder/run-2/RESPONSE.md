I added `currency` to the CSV export, but at the end of the row (after `ts`), not next to `amount`.

Why: `deploy/warehouse/load_ledger.sql` loads the nightly CSV by position (`SELECT c1, c2, c3, c4`, header row skipped). Its comment says new export columns must go at the end. A column inserted beside `amount` would shift `ts` into the warehouse's `posted_at` slot and load wrong data. `deploy/warehouse/schema.sql` also says columns are only ever added at the end. Finance finds columns by header name, so the position makes no difference to them. The warehouse load still works, and it ignores the new fifth field.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`. I extended the comment to say new columns are appended only.
- `tests/test_csv_out.py`: the header test now includes `currency`. I added a test that the currency value is written, and one that the first four columns keep their positions.

I ran the grep across all file types. `reports/monthly.py` reads columns by name, so it is unaffected. The 8 tests pass.

Decision for you: if the warehouse should store currency too, it needs a new `ledger_raw` column (`ALTER TABLE ... ADD COLUMN`) and a `c5` in `load_ledger.sql`. I did not change either, since you only asked for the CSV. If you really want currency beside `amount`, the loader would have to be changed to match first.

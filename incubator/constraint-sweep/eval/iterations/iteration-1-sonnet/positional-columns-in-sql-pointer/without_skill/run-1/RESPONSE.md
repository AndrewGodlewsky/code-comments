I added a `currency` column to the CSV export, but it is the last column, not next to `amount`.

The nightly warehouse load (`deploy/warehouse/load_ledger.sql`) reads the CSV by position (c1..c4) and skips the header row. A column inserted beside `amount` would shift `ts` into the wrong position, and the load would write bad data into `ledger_raw.posted_at`. Finance finds columns by header name, so the position makes no difference to them. Appending avoids touching the load.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `id, account, amount, ts, currency`. The comment now says new columns go at the end.
- `tests/test_csv_out.py`: added tests that currency is written and that the first four columns keep their positions.

All tests pass. The warehouse does not store currency yet: the load ignores the new field. If you want it there, that needs a separate change (an `ALTER TABLE ... ADD COLUMN` plus an updated load SQL). Say so if you want me to do it.

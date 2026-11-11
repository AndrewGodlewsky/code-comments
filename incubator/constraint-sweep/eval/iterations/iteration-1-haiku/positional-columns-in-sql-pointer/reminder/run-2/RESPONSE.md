The nightly CSV export now has `currency` as a column directly after `amount`. The header is `id, account, amount, currency, ts`, and each row carries the entry's ISO 4217 code (for example `EUR`).

Changes:

- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "currency", "ts"]`. The comment now records the warehouse's positional mapping.
- `deploy/warehouse/load_ledger.sql`: this was the constraint I had to handle. The warehouse loader stages each file as `c1..cN` by position and skips the header. The old comment said new columns must go at the end, because a mid-row insert shifts every later field. With `currency` at position 4, the old `SELECT c1, c2, c3, c4` would have loaded the currency code into `posted_at`. The select is now `SELECT c1, c2, c3, c5`, so the warehouse still receives the same four fields with the same meaning. Currency is not loaded into `ledger_raw`, which matches the existing table; adding it would need an `ALTER TABLE ... ADD COLUMN` and a select change, and I did not make that call for you.
- `tests/test_csv_out.py`: a new test asserts that `currency` sits immediately after `amount` and holds `EUR` for the sample entry.

Checked and unaffected: `reports/monthly.py` reads by header name (`csv.DictReader`), so its totals are unchanged. `docs/finance.md` and `README.md` describe the export without naming columns by position. `deploy/warehouse/schema.sql` and `retention.sql` do not touch the export. `deploy/crontab` runs the exporter at 01:00 and the warehouse load at 01:30.

Verification: `python -m unittest discover -s tests -t .` passes, 7 tests.

Action needed before this reaches production: the exporter and `load_ledger.sql` must ship together. If the exporter is deployed alone, tonight's 01:30 load will run the old SQL against the new file and write currency codes into `posted_at`. The two files have to be in the same release. I did not run `warehouse-load` against a real staging table, so the SQL change is verified by reading it, not by running it.

Alternative if you would rather not touch the warehouse SQL: put `currency` at the end of `COLUMNS`. Finance finds columns by name, so this would work for them, but it would not sit next to `amount` as you asked.

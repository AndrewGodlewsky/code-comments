The currency code is now in the CSV export as a column directly after `amount`. The header is `id,account,amount,currency,ts`, and each row carries the entry's ISO 4217 code (for example `EUR`).

One thing had to change beyond the exporter. `deploy/warehouse/load_ledger.sql` loads the file by position (`SELECT c1, c2, c3, c4`), and `ts` was at position 4. With `currency` inserted before it, the timestamp would have loaded into the `posted_at` column as the currency code. I updated the SELECT to `SELECT c1, c2, c3, c5` so `posted_at` still receives `ts`, and rewrote the comment above it to describe the current positions. The currency is not loaded into `ledger_raw`, because that table has no currency column and adding one was not part of this request.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "currency", "ts"]`.
- `deploy/warehouse/load_ledger.sql`: the SELECT maps `ts` to position 5, and the comment now states the positions and says to update the SELECT when `COLUMNS` changes.
- `tests/test_csv_out.py`: new test that `currency` sits immediately after `amount` and holds `EUR` for the sample entry.

Verification: the unit suite passes (7 tests, including the existing monthly-totals test, which reads by header name and is unaffected). I did not run `warehouse-load` against a real staging table, since it is not in this repository. Please check one nightly load before relying on the new layout. The loader's assumption that the staged table has a `c5` field is inferred from the file's width, not confirmed.

Constraint notes: the positional contract in `load_ledger.sql` was live and is kept by updating the SELECT in the same change. The comment in `exporter/csv_out.py` ("reads these fields by position") is still accurate. `reports/monthly.py`, `docs/finance.md` and `schema.sql` do not depend on column position, so they are unchanged.

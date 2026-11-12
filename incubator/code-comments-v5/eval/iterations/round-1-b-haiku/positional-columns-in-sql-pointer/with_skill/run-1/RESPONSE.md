The currency code is now in the nightly CSV export, directly after `amount`. The header is `id, account, amount, currency, ts`.

The warehouse load was the catch. `deploy/warehouse/load_ledger.sql` stages the CSV by position and read `c4` as `posted_at`. With currency in position 4, the timestamp would have landed in the currency slot and every load after this change would have written wrong dates. The load now skips position 4 and reads the timestamp from position 5. `ledger_raw` has no currency column, so nothing else changes in the warehouse. If finance wants currency stored there too, that needs an `ALTER TABLE ... ADD COLUMN` at the end of `schema.sql` and a matching entry in the SELECT.

Changes:
- `exporter/csv_out.py`: `COLUMNS` now puts `currency` after `amount`. The comment says that any change to the column order or count must be matched in the load SQL.
- `deploy/warehouse/load_ledger.sql`: the SELECT reads `c1, c2, c3, c5`. The comment now records the position of each field and replaces the old "new columns go at the end" rule.
- `tests/test_csv_out.py`: a new test checks that `currency` sits right after `amount` and carries the entry's value.

Tests: all 7 pass (`python -m unittest discover -s tests -t .`). I did not run the SQL, since there is no warehouse here. Please check the load on a staging file before tonight's 01:30 run.

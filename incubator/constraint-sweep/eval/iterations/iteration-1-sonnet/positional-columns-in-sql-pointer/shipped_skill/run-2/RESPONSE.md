I added a `currency` column (ISO 4217 code, e.g. `EUR`) to the CSV export, but it is the last column, not next to `amount`.

`deploy/warehouse/load_ledger.sql` reads the file by position (`c1`..`c4`) and skips the header. Putting currency right after `amount` would shift `ts` into `c5` and load currency into `posted_at`. Since finance finds columns by header name, the end position costs them nothing. I kept the warehouse load unchanged, so it ignores the new column and `ledger_raw` does not store currency yet. If you want it in the warehouse, that needs an `ALTER TABLE ... ADD COLUMN` on `ledger_raw` plus `c5` in the load. I did not make that change.

Changes:
- `exporter/csv_out.py`: `currency` appended to `COLUMNS`. I updated the comment to say new columns go at the end.
- `tests/test_csv_out.py`: header check now includes `currency`, plus a test that the value is written.
- `docs/finance.md`: notes that `currency` names the currency of each amount.

I did not run the tests.

I added `currency` to the nightly CSV export, but as the last column, not next to `amount`.

The reason is the warehouse load. `deploy/warehouse/load_ledger.sql` stages the CSV by position (`SELECT c1, c2, c3, c4 FROM export_staging`) and skips the header. If `currency` went between `amount` and `ts`, `ts` would move to position 5 and the nightly load would write the currency code into `posted_at`. Appending at the end keeps every existing field where the load expects it. Finance can still find `currency` by header name, which is how they look up columns.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`.
- `tests/test_csv_out.py`: the header test also checks for `currency`, and a new test checks that the value is written as given (`EUR` for the sample entry).

All 7 unit tests pass. The comments in `csv_out.py` and `load_ledger.sql` were already accurate, so I left them unchanged.

Decision for you: if you want `currency` next to `amount` after all, the load script and the warehouse table have to change first. `load_ledger.sql` needs new position mappings, and `deploy/warehouse/schema.sql` needs a `currency` column added at the end. I did not make those changes because they are deploy-side and affect production loads.

The warehouse table has no currency column yet, so tonight's load will ignore the new field. Adding it means a schema change, which the schema file says is done only by appending columns.

I did not change `docs/finance.md`. It still says amounts are in the entry's own currency, which remains true. You may want to tell finance that the export now has a `currency` column.

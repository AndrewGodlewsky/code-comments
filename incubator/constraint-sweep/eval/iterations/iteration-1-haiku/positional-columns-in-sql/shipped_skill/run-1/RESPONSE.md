Done. The CSV export now has a `currency` column directly after `amount`:

    id, account, amount, currency, ts

Changes:

- `exporter/csv_out.py`: added `currency` to `COLUMNS` in that position, with a comment saying the warehouse load reads fields by position.
- `deploy/warehouse/load_ledger.sql`: the warehouse load stages the file by position, so `ts` moved from `c4` to `c5`. The load now selects `c1, c2, c3, c5`. Without this change, `posted_at` would have been loaded from the currency field on tonight's run. The comment above the statement is updated to match. Please review this, since it is the production load.
- `tests/test_csv_out.py`: the header test now expects `currency`, and a new test checks that `currency` sits right after `amount` and holds `EUR` for the sample entry.

Things you need to know:

- The warehouse load is positional, and `docs/finance.md` and `reports/monthly.py` read by header name. The request said the order was ours to choose, but for the warehouse it is not, so the loader had to change with the column.
- The warehouse does not receive `currency`. `ledger_raw` has no currency column and the load does not map one. If the warehouse needs it, that is a schema change (added at the end of the table, per `deploy/warehouse/schema.sql`) plus a new `c4` mapping.
- I assumed `export_staging` has at least five columns. That depends on how `warehouse-load` builds the staging table from the file header, which I could not check from this repository. Please confirm it on the next run.
- `reports/monthly.py` is unaffected because it reads `account` and `amount` by name.
- The unit tests pass: `python -m unittest discover -s tests -t .` ran 7 tests, all OK.

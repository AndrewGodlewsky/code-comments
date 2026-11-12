The currency code is now in the nightly CSV export, but as the last column, not next to `amount`.

Your note says finance finds columns by header name, so the order is up to us. That holds for finance and for `reports/monthly.py`, which reads by header. It does not hold for the nightly warehouse load. `deploy/warehouse/load_ledger.sql` stages each file as `export_staging(c1, c2, ...)` and selects `c1..c4` by position. If `currency` went between `amount` and `ts`, `ts` would load into `posted_at` as the currency code and the timestamps would be lost. Appending the column keeps every existing position unchanged.

What changed (all inside the repository):
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`. I added a comment above it saying new columns must be appended, because the warehouse load reads by position.
- `tests/test_csv_out.py`: added `test_currency_is_written_after_the_existing_columns`, which checks the full header order and that the currency value is `EUR`.

`python -m unittest discover -s tests -t .` passes (7 tests).

Not changed, and needing a decision from you:
- The warehouse table `ledger_raw` and `load_ledger.sql` do not load `currency`. The export now carries it, but nothing stores it yet. Adding it means a `schema.sql` change (appended column) and a `load_ledger.sql` change (`c5`). I did not make those, since they touch the production load.
- If you want currency next to amount in the file itself, the loader has to match by header name first. That is a change to `warehouse-load`, which is outside this repository.

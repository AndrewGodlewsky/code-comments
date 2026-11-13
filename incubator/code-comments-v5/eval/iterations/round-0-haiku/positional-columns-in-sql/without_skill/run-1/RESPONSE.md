Finance's currency code is now in the nightly CSV export as a `currency` column, directly after `amount`. The export order is now `id, account, amount, currency, ts`.

One thing you need to know: the warehouse loader reads the CSV by position, not by header name. `deploy/warehouse/load_ledger.sql` maps `c1..c4` onto the ledger table, so inserting `currency` before `ts` would have loaded the currency code into `posted_at` on tonight's run. To avoid that, I changed the mapping to `SELECT c1, c2, c3, c5`, which skips `currency` and keeps `ts` going into `posted_at`. The table schema is unchanged, so the warehouse does not receive currency; this change only affects the CSV.

Changes:
- `exporter/csv_out.py`: `COLUMNS` now includes `currency` between `amount` and `ts`.
- `deploy/warehouse/load_ledger.sql`: reads `c5` for `posted_at` and skips `c4`. The comment explains the order contract.
- `tests/test_csv_out.py`: the header test checks for `currency`, and a new test checks that it sits right after `amount` and holds the entry's currency.

Tests: all 7 unit tests pass (`python -m unittest discover -s tests -t .`). I did not run the warehouse load, since I have no warehouse here. Please check the next nightly load, or run `warehouse-load` against a copy of tonight's file, before relying on it.

Finance's `reports/monthly.py` reads by header name, so it is unaffected.

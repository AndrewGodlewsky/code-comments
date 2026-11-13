The currency code is now in the nightly CSV export as a `currency` column, directly after `amount`. The CSV header is `id,account,amount,currency,ts`, and each row carries the entry's ISO 4217 code (for example `EUR`).

One thing you need to know before this ships: the warehouse load reads the CSV by position, not by header name. `deploy/warehouse/load_ledger.sql` stages each file as `c1..cN` and maps `c4` to `posted_at`. Inserting `currency` before `ts` would have pushed `ts` into `c5` and loaded the currency code into `posted_at` on every row. I updated the load so `posted_at` now comes from `c5`, and `currency` (`c4`) is not loaded into `ledger_raw`. The comment in that file now records the current column order.

Changes:
- `exporter/csv_out.py`: `COLUMNS` now includes `currency` between `amount` and `ts`.
- `deploy/warehouse/load_ledger.sql`: `SELECT c1, c2, c3, c5` and an updated comment on the column contract.
- `tests/test_csv_out.py`: the header test now covers `currency`, and two new tests check that `currency` sits right after `amount` and that its value is written for each entry.

Tests: `python -m unittest discover -s tests -t .` passes (8 tests).

Deployment: the export (cron at 01:00) and the warehouse load (cron at 01:30) must ship from the same checkout, so the new column order and the new load mapping go live together. If the export runs with the new order before the load mapping is updated, the nightly load will write wrong data into `posted_at`. I have not run the warehouse load itself, because `warehouse-load` and the warehouse are not available in this repository.

If you would rather avoid touching the warehouse SQL, the alternative is to append `currency` after `ts`. That is the order the load comment asks for, and it needs no SQL change. Finance looks up columns by header name, so either order works for them. I went with the side-by-side placement you asked for.

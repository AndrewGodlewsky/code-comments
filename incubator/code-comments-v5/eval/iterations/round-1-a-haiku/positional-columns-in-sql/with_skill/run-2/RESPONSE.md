Done. The nightly CSV export now has a `currency` column directly after `amount`:

    id, account, amount, currency, ts

Changes:

- `exporter/csv_out.py`: `COLUMNS` now includes `currency` after `amount`. I added a comment that the order matters, because the warehouse loader reads fields by position.
- `deploy/warehouse/load_ledger.sql`: this needed a change. The loader stages each CSV row as c1..cN and maps them by position. With currency in position 4, the old `SELECT c1, c2, c3, c4` would have loaded the currency code into `posted_at`, and the timestamp would have been lost. The loader now reads `c5` for `posted_at`. Currency is not loaded, because `ledger_raw` has no currency column, and the comment above the query says so. The old comment said new columns must go at the end; that was no longer true, so I rewrote it to describe the current layout.
- `tests/test_csv_out.py`: the header test now includes `currency`, and a new test checks that `currency` sits directly after `amount` and holds the entry's code.

Verification: `python -m unittest discover -s tests -t .` runs 7 tests, all passing. I did not run the warehouse SQL, because `warehouse-load` is not available here, so the `c5` mapping is untested against a real load.

Things to check before the next nightly run:

1. The 01:30 cron job runs `warehouse-load` with the new `load_ledger.sql`. Please confirm the staging step maps fields the way the comment says. If `export_staging` is built some other way, the `c5` mapping is wrong.
2. Currency is in the CSV but not in the warehouse. If the warehouse should store it, `ledger_raw` needs a new column added at the end (`ALTER TABLE ... ADD COLUMN`), plus a matching change to the load. I did not make that change because it was not requested.
3. Files that read the CSV by name, such as `reports/monthly.py` (it uses `DictReader`) and the finance docs, are unaffected.

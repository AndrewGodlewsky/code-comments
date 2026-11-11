The nightly CSV export now has a `currency` column directly after `amount`:

    id,account,amount,currency,ts

One thing had to change beyond the exporter. `deploy/warehouse/load_ledger.sql` loads the CSV by position (the header row is skipped, and fields are staged as c1, c2, ...). It mapped `posted_at` to c4, which is now the currency column, so `ts` would have loaded into the wrong place. I changed the SELECT to `c1, c2, c3, c5` so `posted_at` still receives the timestamp, and updated the comment above it to say why. Nothing else in the warehouse changes: `schema.sql` is untouched and currency is not loaded into `ledger_raw`, since you did not ask for that.

Changes:
- `exporter/csv_out.py`: `COLUMNS` now includes `currency` between `amount` and `ts`.
- `deploy/warehouse/load_ledger.sql`: `posted_at` now reads c5; comment updated.
- `tests/test_csv_out.py`: header test includes `currency`, and a new test checks it sits right after `amount`.

Tests: all 7 unit tests pass (`python -m unittest discover -s tests -t .`).

Before the first deploy, the warehouse load needs to ship with the CSV change, because the cron jobs run the exporter at 01:00 and the load at 01:30 from the same repo. If the exporter goes out without the SQL change, the nightly load will put timestamps into the wrong column.

Not changed: `reports/monthly.py` reads columns by header name, and `docs/finance.md` says order does not matter to finance, so both are unaffected.

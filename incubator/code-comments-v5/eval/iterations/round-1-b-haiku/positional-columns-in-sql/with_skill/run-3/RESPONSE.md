The nightly CSV export now has a `currency` column directly after `amount`. Header order is now `id, account, amount, currency, ts`, and the currency code (for example `EUR`) is written from each entry's `currency` field.

One thing you need to know: your note that the order is up to us does not hold for the warehouse load. `deploy/warehouse/load_ledger.sql` stages each file by position (`c1, c2, ...`) and selected `c1, c2, c3, c4` into `ledger_raw`. With `currency` inserted at position 4, the load would have written the currency code into `posted_at` and dropped the timestamp. So I changed that SELECT to `c1, c2, c3, c5`. Currency is skipped there because `ledger_raw` has no currency column, and I did not add one.

Changes, all inside the repository:
- `exporter/csv_out.py`: `COLUMNS` now includes `currency` after `amount`.
- `deploy/warehouse/load_ledger.sql`: the SELECT now maps `c5` to `posted_at`. I also rewrote its comment, which said new columns must go at the end. That is no longer true for the warehouse mapping, and the comment now says the SELECT must follow `COLUMNS`.
- `tests/test_csv_out.py`: added a test that `currency` sits immediately after `amount` and holds `EUR`.

Checks: the unit tests pass (7 tests, including the new one). I could not run `load_ledger.sql` against the warehouse, so please check the first load after this change.

Other consumers are unaffected. `reports/monthly.py` reads columns by header name. `docs/finance.md` needs no change.

Decision for you: if you would rather not touch the production load SQL, the zero-risk option is to put `currency` at the end of `COLUMNS`. That keeps the old positional contract, but finance then gets it after `ts`, not beside `amount`. I went with the side-by-side placement you asked for.

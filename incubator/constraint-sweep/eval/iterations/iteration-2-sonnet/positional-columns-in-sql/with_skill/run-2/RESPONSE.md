Done. `currency` is now a column in the CSV export, directly after `amount` (order: id, account, amount, currency, ts). Tests pass, including a new one for the placement.

Changes:
- `exporter/csv_out.py`: added `"currency"` to `COLUMNS` after `"amount"`.
- `tests/test_csv_out.py`: header test now expects `currency`; new test checks it sits right after `amount` with the right value.
- `deploy/warehouse/load_ledger.sql`: see below.

Constraint that shaped the change (`deploy/warehouse/load_ledger.sql:2-6`): the nightly warehouse load reads the CSV by position (`c1..cN`, header skipped) and said new columns must go at the end, otherwise later fields load into the wrong column. Finance finds columns by header name, but the load does not. You asked for the column next to `amount`, so I kept that and updated the load in the same change. The SELECT is now `c1, c2, c3, c5`, so `ts` still lands in `posted_at` and `currency` (`c4`) is not loaded. I rewrote the header comment, which the change made false. Without this edit the 01:30 load would have put the currency code into `posted_at`, and the load would have silently produced bad data.

Decision for you: `ledger_raw` has no currency column, so the warehouse does not store currency yet. If you want it there, add the column with `ALTER TABLE ... ADD COLUMN` (`schema.sql` only allows additions at the end) and add `c4` to the load. I did not do this since it was not requested.

Rollout note: the cron exports at 01:00 and loads at 01:30, so deploy the code and the SQL together. A file exported with the old column order must not be loaded by the new SQL.

Other mentions checked and left alone: `reports/monthly.py` reads by header name (`account`, `amount`) and is unaffected; `docs/finance.md` and `retention.sql` need no change.

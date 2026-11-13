The CSV export now has a `currency` column directly after `amount`. The order is now id, account, amount, currency, ts. I ran the existing test suite and it passes.

Putting it next to `amount` moves `ts` from the fourth column to the fifth, and the nightly warehouse load reads columns by position. `deploy/warehouse/load_ledger.sql:2-6` says new export columns have to go at the end. Otherwise every field after the new one loads into the wrong column. If I had only changed `exporter/csv_out.py`, `ts` would have loaded the currency code into `posted_at`, and the retention job would have started deleting rows based on bad dates. So I changed the load as well.

- `exporter/csv_out.py`: added `currency` to `COLUMNS` after `amount`.
- `deploy/warehouse/load_ledger.sql`: the select is now `c1, c2, c3, c5`, so `posted_at` still comes from `ts`. I rewrote the comment to describe the new column order. Currency is not loaded into the warehouse, because `ledger_raw` has no column for it and you didn't ask for one. If finance wants it there too, that needs an `ALTER TABLE ... ADD COLUMN` on `ledger_raw`.
- `tests/test_csv_out.py`: the header test now checks for `currency`.
- `docs/finance.md`: now says where the currency is given.

**Deploy order.** The exporter and the load SQL have to go out together. The exporter runs at 01:00 and the load at 01:30 (`deploy/crontab`). If one is deployed without the other, that night's load fills `posted_at` with the wrong field.

**Staleness.** `deploy/warehouse/schema.sql:2` says columns are only ever added at the end. That is true of the warehouse table, which I didn't touch, so I left it alone.

`reports/monthly.py` finds columns by header name, so it is unaffected.

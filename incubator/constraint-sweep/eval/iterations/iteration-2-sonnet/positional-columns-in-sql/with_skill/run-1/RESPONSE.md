The CSV export now has a `currency` column right after `amount`. The columns are `id, account, amount, currency, ts`. The change is in `exporter/csv_out.py`, and I added `currency` to the header check in `tests/test_csv_out.py`. The tests pass.

Finance finds columns by header name, but the nightly warehouse load does not. `deploy/warehouse/load_ledger.sql:2-6` reads the CSV by position (`c1`..`c4`) and skips the header row. Its comment said new columns must go at the end. Putting currency next to amount would have shifted `ts` to `c5`, and the load would have put the currency code into `posted_at`.

I kept the placement you asked for and changed the load instead. `deploy/warehouse/load_ledger.sql` now selects `c1, c2, c3, c5`, so it skips the currency field. I also rewrote its header comment to match, since the old "add columns at the end" wording was no longer true.

- **Deploy together:** the load SQL and the exporter change must go out at the same time. If the exporter ships first, the 01:30 load will break. If the load SQL ships first, the old CSV will break it.
- **Currency not stored:** the warehouse does not store currency. `ledger_raw` has no such column, and `schema.sql` says columns are only added at the end. I did not touch the schema. If you want currency in the warehouse, that needs an `ALTER TABLE ... ADD COLUMN` plus a load change.
- **Other readers:** `reports/monthly.py` reads by header name, so it is unaffected. `retention.sql` does not touch the CSV.

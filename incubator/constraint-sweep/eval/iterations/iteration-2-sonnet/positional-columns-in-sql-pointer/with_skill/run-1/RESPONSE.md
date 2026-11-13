The CSV export now has a `currency` column directly after `amount`. The columns are `id, account, amount, currency, ts`. The unit tests pass, and I added one that checks currency sits right after amount.

One thing you might not expect: `deploy/warehouse/load_ledger.sql` reads the CSV by position and skips the header (lines 2-6, and `exporter/csv_out.py:4` says the same). Inserting currency in the middle would have shifted `ts` into the wrong column in the nightly warehouse load. I changed that load to `SELECT c1, c2, c3, c5` so `posted_at` still comes from the timestamp. I also updated its comment to list the current column order.

- **Not tested:** I didn't run the nightly warehouse load, only the Python tests. The exporter and the SQL change need to deploy together, because the 01:00 export and the 01:30 load run from the same checkout.
- **Currency not loaded:** `ledger_raw` has no currency column, so the warehouse ignores the new field. Loading it would mean an `ALTER TABLE ... ADD COLUMN` in `schema.sql` and a matching insert. I left that alone because you didn't ask for it.
- **Other readers:** `reports/monthly.py` and `docs/finance.md` find columns by header name, so they are unaffected.
- **Stale text:** nothing else stale found. The "new export columns go at the end" rule in `load_ledger.sql` was replaced by the instruction to update the c-numbers when a column is added or moved.

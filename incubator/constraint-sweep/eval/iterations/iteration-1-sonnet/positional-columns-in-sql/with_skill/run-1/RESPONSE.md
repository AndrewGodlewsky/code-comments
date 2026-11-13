Done: the CSV now has a `currency` column right after `amount` (header order: id, account, amount, currency, ts). Change is in `exporter/csv_out.py`; I updated the header test in `tests/test_csv_out.py`. Tests pass.

Constraint that shaped the change:
- `deploy/warehouse/load_ledger.sql:1-6` said fields are loaded by position (c1, c2, ...) and that new columns must go at the end. Inserting currency before `ts` would have loaded currency into `posted_at` and broken the nightly load and the 7-year retention delete (`deploy/warehouse/retention.sql`). You asked for the column next to amount, so I kept that position and changed the load instead: it now reads `SELECT c1, c2, c3, c5` (skipping the new c4) and its comment lists the new positions. The warehouse table is unchanged, so currency is not stored there yet. If you want it in the warehouse, `ledger_raw` needs an `ALTER TABLE ... ADD COLUMN currency` (schema.sql says columns are only added at the end) and the load needs to select c4 into it. That is a production migration, so I left it for you.
- Deploy together: the new CSV layout and the new `load_ledger.sql` must go live together, or the 01:30 load will put the wrong fields in the wrong columns.

Checked and unaffected: `reports/monthly.py` reads by header name, as does finance (`docs/finance.md`).

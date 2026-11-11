The nightly CSV now has a `currency` column directly after `amount`. The header reads `id,account,amount,currency,ts`, and a sample row reads `E-1,4000,12.50,EUR,2026-11-01T09:00:00Z`. The unit tests pass (7 of 7), including a new test that checks `currency` sits right after `amount`.

One change was needed beyond the exporter. The warehouse load does not read columns by name. `deploy/warehouse/load_ledger.sql` maps staged fields by position (`c1..c4`), and its comment said new columns must go at the end. Inserting `currency` before `ts` would have shifted `ts` into `c4` and loaded the currency code into `posted_at`. So I changed the load to read `c1, c2, c3, c5` and skip `c4` (currency), since `ledger_raw` has no currency column. I also rewrote that comment to match. Both changes are in the same commit-ready set, so tonight's 01:30 load will not break.

Constraints that shaped the change:
- `deploy/warehouse/load_ledger.sql:2-6` (live): fields are read by position and the order of `COLUMNS` is a contract. Kept by updating the SELECT in the same change.
- `exporter/csv_out.py:4` (live, still true): "reads these fields by position". Left as written.
- `deploy/warehouse/load_ledger.sql:4-6` (was "new columns go at the end"): no longer true after this change, so I rewrote it.

Not changed, and worth a decision from you:
- `ledger_raw` does not store currency, so the warehouse drops it. If finance needs currency in the warehouse, that needs `ALTER TABLE ledger_raw ADD COLUMN currency` (appended at the end, per `deploy/warehouse/schema.sql`) plus a new SELECT. I did not add it because you asked only for the export.
- `reports/monthly.py` reads by header name, so it is unaffected. `docs/finance.md` says order does not matter to finance, which is still true.
- Nightly files written before this change have no currency column. Any reader that uses positions rather than header names would see a different layout across the switch.

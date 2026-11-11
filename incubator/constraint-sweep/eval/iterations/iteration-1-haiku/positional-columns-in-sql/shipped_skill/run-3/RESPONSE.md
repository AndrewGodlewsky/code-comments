I added `currency` to the nightly CSV export, directly after `amount`. The header is now `id, account, amount, currency, ts`, and the change is in `exporter/csv_out.py`. I also added a test that checks the two columns sit side by side. All 7 unit tests pass.

Please do not deploy this yet. `deploy/warehouse/load_ledger.sql` loads the export by position: it stages the fields as c1..c5 and selects c1..c4 into `ledger_raw`. After this change, c4 is `currency` and `ts` moves to c5, so the nightly load would write currency into `posted_at` and drop the timestamp. It would not fail, so the bad data would be silent. That SQL comment also says new columns belong at the end. I did not change the SQL, because the warehouse side needs an owner's decision. The options are:

1. Update `load_ledger.sql` to select c1, c2, c3, c5 for the current `ledger_raw` table, and add a currency column to the warehouse table first if finance needs it there.
2. Keep `currency` at the end of the export. The warehouse load then keeps working, and finance can still find the column by header name.

I also added a short comment above `COLUMNS` in `exporter/csv_out.py` that points to the warehouse load, so the next person who reorders columns sees the dependency.

Nothing else changed. `docs/finance.md` and `reports/monthly.py` both look up columns by header name, so they are unaffected.

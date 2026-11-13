Added the currency code to the nightly CSV export as a column right after amount. The header is now id, account, amount, currency, ts, and the currency value is written from each entry's currency field (for example EUR).

One dependent site had to change with it. deploy/warehouse/load_ledger.sql loads the CSV by field position, and it read posted_at from c4. With currency inserted at c4, ts moved to c5, so the load would have written currency into posted_at. The load now reads c1, c2, c3 and c5, and currency (c4) is not loaded because ledger_raw has no currency column. The comment in that file that said new columns must go at the end is rewritten, since it is no longer true for this change.

Also added a test that checks currency sits directly after amount in the header and holds EUR in the row. The unit tests pass (7 of 7).

Finance's monthly report (reports/monthly.py) reads by header name, so it is unaffected. Two things to decide before the next nightly run:
- If finance wants currency in the warehouse table too, that needs a schema change (ALTER TABLE ... ADD COLUMN, at the end) and a matching edit to load_ledger.sql. I did not make it, because the request was for the export only.
- Existing nightly files in /data/export keep the old four-column layout. They are not loaded again, but any manual reload of an old file through load_ledger.sql would now misplace ts. Reloads of old files need the old SELECT.

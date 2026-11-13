The currency code is now a column in the nightly CSV, directly after `amount`. The header is `id, account, amount, currency, ts`, and each row carries the entry's ISO 4217 code (for example `EUR`). The change is in `exporter/csv_out.py`, and I added a test that checks `currency` sits right after `amount`. All 7 unit tests pass.

Your note that the column order is up to us does not hold for production. `deploy/warehouse/load_ledger.sql` stages the file by position (`c1`, `c2`, ...) and skips the header, so inserting a column in the middle shifts every field after it. Without a fix, the nightly `warehouse-load` would have written `currency` into `posted_at` and left `ts` out, silently and with no error. I changed the load's `SELECT` to read `c1, c2, c3, c5`, which keeps `ledger_raw` unchanged and leaves `currency` unloaded. I also rewrote the comment in that file that said new columns must go at the end, because that rule no longer applies. The positional dependency is now noted beside `COLUMNS` in `exporter/csv_out.py`.

Please check two things:
1. Whether finance wants `currency` stored in the warehouse. If so, `ledger_raw` needs a new column added at the end, and the load should map it. That is a schema change I did not make.
2. The next nightly run should be checked once. I could not run the warehouse load here, so the fixed mapping is verified only by reading it against the file layout, not by an actual load.

Unchanged: `docs/finance.md` still holds, since finance finds columns by name, and `reports/monthly.py` reads by header name, so it is unaffected.

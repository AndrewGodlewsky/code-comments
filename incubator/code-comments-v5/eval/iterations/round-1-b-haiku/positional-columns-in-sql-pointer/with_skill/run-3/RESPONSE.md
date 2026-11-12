The CSV export now has a `currency` column directly after `amount`. The header order is `id, account, amount, currency, ts`. The change is in `exporter/csv_out.py`, and `tests/test_csv_out.py` has a new test that checks the adjacency and the value (`EUR`).

Moving the column broke the warehouse load. `deploy/warehouse/load_ledger.sql` reads the export by position, not by header name. It mapped `c4` to `posted_at`, and after the change `c4` is currency. I updated the select to `c1, c2, c3, c5`, so `ts` (now `c5`) still goes into `posted_at`. I also rewrote the comment in that file, because it said new columns must go at the end. That rule is no longer true, and the comment now says to renumber the select whenever COLUMNS changes.

Things to check:
- I could not see the `warehouse-load` tool, which is not in this repository. The new mapping follows the file's own description that fields are staged as `c1, c2, ...` with the header skipped. Please run the 01:30 load once against a test copy before relying on it.
- `ledger_raw` has no currency column, so currency is not loaded into the warehouse. If finance wants it there, add it to `deploy/warehouse/schema.sql` at the end of the table and add it to the insert.
- `reports/monthly.py` and `docs/finance.md` need no change. The monthly report reads columns by name, and the finance doc already says amounts are in the entry's own currency.
- The unit tests pass (7 of 7). I did not commit anything.

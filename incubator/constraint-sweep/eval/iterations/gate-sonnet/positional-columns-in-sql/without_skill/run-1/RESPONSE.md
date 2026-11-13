I added `currency` to the CSV export, but as the last column (after `ts`), not directly next to `amount`.

Why: `warehouse/load.sql` reads the CSV fields by position (c1..c4) and skips the header. Putting `currency` between `amount` and `ts` would shift `ts` into the wrong warehouse column on the next nightly load. The loader's own notes say new columns go at the end. Appending leaves the existing four columns where they are, and the loader ignores the extra fifth field.

Finance finds columns by header name (see `docs/finance.md`), so they will see `currency` in the file. It just won't sit beside `amount`.

If you want them adjacent, that needs a coordinated change: update `warehouse/load.sql` (and probably `ledger_raw`) to the new order and deploy it together with the exporter change. Tell me if you want that.

Changes: `exporter/csv_out.py` (added the column, plus a comment about the ordering constraint) and `tests/test_csv_out.py` (tests for the currency value and for the first four column positions staying fixed).

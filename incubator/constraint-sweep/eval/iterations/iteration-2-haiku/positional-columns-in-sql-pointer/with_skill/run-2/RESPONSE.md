The CSV export now has a `currency` column right after `amount`. The header is `id,account,amount,currency,ts`, and each row carries the entry's ISO 4217 code (for example `EUR`).

The nightly warehouse load reads the CSV by position, not by header name. Moving `ts` from column 4 to column 5 would have sent timestamps into the wrong place, so I changed the load in the same edit:

- `deploy/warehouse/load_ledger.sql` now selects `c1, c2, c3, c5`, so `posted_at` still gets `ts`. `currency` (`c4`) is not loaded, because `ledger_raw` has no currency column. I rewrote the file's comment to give the current position mapping, since the old comment said new columns must go at the end, which is no longer true.
- `exporter/csv_out.py` lists the new column in `COLUMNS`.
- `tests/test_csv_out.py` has a new test that checks currency sits directly after amount.

Unit tests pass (7 of 7), and a sample export produced the expected header and row.

Before this ships, check the following:
- The warehouse load and the export must deploy together. A CSV written before the change, loaded after it (or the reverse), will put fields in the wrong columns.
- If finance wants currency in the warehouse table, that needs a new column added at the end of `ledger_raw` and a matching change to the select.

If you would rather keep the old load untouched, the alternative is to append `currency` after `ts`. That keeps the SQL as it was but does not place currency next to amount.

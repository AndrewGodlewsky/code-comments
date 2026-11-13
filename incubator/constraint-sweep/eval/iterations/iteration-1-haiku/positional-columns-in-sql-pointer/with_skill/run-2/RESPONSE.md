The CSV export now has a `currency` column directly after `amount`. The header is `id,account,amount,currency,ts`, and each row carries the entry's ISO 4217 code (for example `EUR`).

One thing had to change with it. The warehouse loader, `deploy/warehouse/load_ledger.sql`, reads the export by position, not by header name. Its `SELECT` used `c4` for `posted_at`, which after this change would be `currency`, so every night the timestamps would have landed in the currency position. I updated it to read `c5` for `posted_at`, and rewrote its comment to list the current column order. The loaded table is unchanged: `ledger_raw` has no currency column, and I did not add one, since you only asked for the CSV.

Changes:
- `exporter/csv_out.py`: `COLUMNS` now includes `currency` between `amount` and `ts`.
- `deploy/warehouse/load_ledger.sql`: `posted_at` is read from `c5`, and the comment documents the positions.
- `tests/test_csv_out.py`: added a test that `currency` sits right after `amount` and carries the entry's code.

The unit tests pass (7 of 7).

Decision for you: if finance wants currency in the warehouse too, that needs a `currency` column added to `ledger_raw` at the end of the table (the schema comment says columns are only added at the end) and a `c4` mapping in the load. I left that out.

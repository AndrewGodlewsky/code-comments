I added `currency` to the CSV export, but as the last column, not next to `amount`.

The file is now `id,account,amount,ts,currency`, with one `EUR`-style ISO 4217 code per row. I changed `COLUMNS` in `exporter/csv_out.py`, added a test for the new column in `tests/test_csv_out.py`, and added a line about the column to `docs/finance.md`. All 7 unit tests pass.

I did not put it beside `amount` because the warehouse load is positional. `deploy/warehouse/load_ledger.sql` stages each file as `c1..cN` and maps `c1..c4` to `entry_id, account_code, amount, posted_at`. Putting `currency` between `amount` and `ts` would have loaded the currency code into `posted_at` every night. The SQL comment already says new export columns must go at the end. Finance finds columns by header name, so the position does not affect them.

The warehouse load is unchanged, so `currency` is not loaded into `ledger_raw`. That matches the current schema.

If you do want the two side by side, that is a coordinated change. `load_ledger.sql` would need to select `c1, c2, c3, c5` and the schema might need a currency column. It would also need to deploy together with the exporter, because the 01:00 export and the 01:30 load run on the same night. I have not made that change.

I added `currency` to the nightly CSV export, but as the last column rather than right next to `amount`.

The reason: `deploy/warehouse/load_ledger.sql` loads the file by position (`SELECT c1, c2, c3, c4 FROM export_staging`) and skips the header. If `currency` went between `amount` and `ts`, the nightly load would put the timestamp into the `amount` column and the currency code into the timestamp column. `schema.sql` also only allows new columns to be appended. Finance finds columns by header name, so their order does not matter to them. The only thing that depends on order is the warehouse load.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`, with a comment that new columns go at the end.
- `tests/test_csv_out.py`: the header check includes `currency`, and a new test checks the exact header and that the value is `EUR` for the sample entry. All 7 tests pass.
- `docs/finance.md`: one sentence describing the `currency` column.

Nothing under `deploy/` changed, and the warehouse load still reads the same four fields.

If you want `currency` beside `amount` for the spreadsheet, the warehouse side needs to change first. `load_ledger.sql` would need to read the new positions, and `ledger_raw` would need a `currency` column added at the end. Files already staged under the old layout would also need handling. I can do that as a separate change if you want it.

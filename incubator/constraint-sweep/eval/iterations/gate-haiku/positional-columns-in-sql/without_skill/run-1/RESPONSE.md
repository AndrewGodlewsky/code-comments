I've added the currency code to the CSV export, but as the last column (after `ts`), not directly next to `amount`.

The reason is the warehouse. `warehouse/load.sql` reads the staged export by position (`c1`..`c4` map to `entry_id`, `account_code`, `amount`, `posted_at`) and skips the header row. If currency went between `amount` and `ts`, the nightly load would write currency codes into `posted_at` and timestamps would be lost. The loader's own comment says new export columns must go at the end for this reason.

Finance reads the file by header name (`docs/finance.md`), so column order doesn't affect them. Appending is safe for them too.

What changed in `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`, with a comment recording that the order is a contract. In `tests/test_csv_out.py` I added a test that checks the header and row, including `EUR` at the end. All 6 tests pass.

If you still want currency beside amount, the warehouse loader has to change first. `load.sql` would need to map `c5` to `posted_at`, and `schema.sql` would need a currency column. I haven't made that change, since it touches the warehouse and needs a decision from whoever owns the load.

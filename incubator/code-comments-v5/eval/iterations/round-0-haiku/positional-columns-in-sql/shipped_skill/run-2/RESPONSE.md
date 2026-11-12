I added `currency` to the nightly CSV export, but as the last column, not next to `amount`.

The reason is `deploy/warehouse/load_ledger.sql`. It stages each file as `export_staging(c1, c2, ...)` and selects fields by position (`c1` to `c4` into `entry_id, account_code, amount, posted_at`). Its header comment says new export columns must go at the end. If `currency` sat between `amount` and `ts`, `ts` would move to position 5, which the load never reads, and the warehouse would load the currency code into `posted_at`.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`, with a comment pointing to the warehouse load's positional contract.
- `tests/test_csv_out.py`: the header test also checks for `currency`.

Output row: `id,account,amount,ts,currency` then `E-1,4000,12.50,2026-11-01T09:00:00Z,EUR`. The unit tests pass (6 of 6). I did not touch the warehouse SQL or schema.

Decision for you: if finance needs `currency` directly beside `amount`, the warehouse load must change first. `load_ledger.sql` would need to map positions for the new order, and `schema.sql` would need a `currency` column. The schema comment says columns are only added at the end, so that is a deliberate change to the warehouse contract. Tell me if you want that done, or whether end placement is acceptable to finance, which already finds columns by header name.

I did not commit or push, since git was out of scope for this run.

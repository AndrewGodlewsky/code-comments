Hi,

I added the currency code to the nightly CSV export as a new `currency` column, but I put it at the end of the row, after `ts`, not directly next to `amount`.

The reason is the warehouse load. `deploy/warehouse/load_ledger.sql` does not read the CSV by header. It stages each file by position and selects `c1, c2, c3, c4` into `entry_id, account_code, amount, posted_at`. If `currency` went between `amount` and `ts`, it would become `c4`, and `posted_at` would receive the currency code while the real timestamp in `c5` is silently dropped. Every nightly load would corrupt `posted_at` without any error. The SQL file's own comment says new columns must go at the end for this reason.

Appending at the end avoids that. Finance still finds `currency` by header name, which is how they already work, so the order does not affect them.

What changed:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`, with a comment that positional consumers depend on the order.
- `tests/test_csv_out.py`: the header test now checks for `currency`, plus two new tests: the first four columns keep their positions, and `currency` carries the entry's value (`EUR` in the fixture).

All 8 tests pass (`python -m unittest discover -s tests -t .`). `reports/monthly.py` reads by header name, so it is unaffected.

If you still want `currency` directly beside `amount`, the warehouse side has to change first. `load_ledger.sql` would need to select `c1, c2, c3, c5` (and the staging mapping would need checking against `warehouse-load`), and that is a production change I did not make or test here. Tell me if you want that done as a separate change.

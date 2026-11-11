I added the currency code to the CSV export, but as the last column instead of next to amount. The columns are now `id, account, amount, ts, currency`.

Why not beside amount: the nightly warehouse load (`deploy/warehouse/load_ledger.sql`) reads the CSV by position (`c1..c4`) and skips the header. Inserting currency after amount would shift `ts` into the wrong column and load bad data. Finance finds columns by header name, so for them the position makes no difference.

I left the warehouse load alone, so the currency value is not loaded into the warehouse yet. Doing that needs a `currency` column on `ledger_raw` (`ALTER TABLE ... ADD COLUMN`), then `c5` added to the load query. Tell me if you want that done. If you still want currency next to amount, the load query and the table would have to change together first.

Changes:
- `exporter/csv_out.py`: added `currency` to `COLUMNS`, with a comment saying the order is positional for the warehouse load and new columns go at the end.
- `tests/test_csv_out.py`: the header test now checks for currency. New tests check the currency value and that the first four columns keep their positions.

I ran the unit tests and they pass.

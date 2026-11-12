I added `currency` to the nightly CSV export, but as the last column, not directly after `amount`.

The header is now `id, account, amount, ts, currency`. Each row carries the entry's ISO 4217 code (for example `EUR`) from `Entry.currency`.

Why not next to `amount`: `deploy/warehouse/load_ledger.sql` stages the file by position (`c1..c4`) and skips the header. Putting `currency` between `amount` and `ts` would make the nightly load write the currency code into `posted_at` and the timestamp into nothing, and the 01:30 `warehouse-load` run would corrupt the warehouse. The loader comment already says new columns go at the end. Finance finds columns by header name, so the position is safe for them.

Changes:
- `exporter/csv_out.py`: `COLUMNS` now ends with `"currency"`.
- `tests/test_csv_out.py`: the header test also checks for `currency`, and a new test checks that it is the last header and holds `EUR` for the sample entry.

`python -m unittest discover -s tests -t .` passes (7 tests).

If you still want `currency` beside `amount`, the loader and the warehouse table both need to change first: `load_ledger.sql` would have to map the new positions, and `deploy/warehouse/schema.sql` would need a new column. That is a production change, so I did not make it here.

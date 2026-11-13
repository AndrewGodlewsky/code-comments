I added `currency` to the CSV export, but as the last column, not directly beside `amount`.

The reason is the warehouse loader. `warehouse/load.sql` reads the export by position (`SELECT c1, c2, c3, c4 FROM export_staging`), and its comment says new export columns must go at the end. If `currency` sat between `amount` and `ts`, `ts` would shift into the `posted_at` slot and every field after it would load into the wrong column.

What changed:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`.
- `tests/test_csv_out.py`: the header test checks for `currency`, and a new test checks that it is the last column and holds the entry's currency (`EUR`).

The unit tests pass (6 tests).

Finance finds columns by header name (`docs/finance.md`), so the new column is usable without a reorder.

If you do need `currency` next to `amount`, the warehouse side has to change in the same release:
1. Add `currency` to `ledger_raw` in `warehouse/schema.sql` with an `ALTER TABLE ... ADD COLUMN`.
2. Update `warehouse/load.sql` to read the new positions (`c1, c2, c3, c5, c4`, with `c4` as `currency` and `c5` as `posted_at`).

I have not made those warehouse changes, because they alter the loaded table and the loader's contract, which should be agreed with whoever owns the warehouse.

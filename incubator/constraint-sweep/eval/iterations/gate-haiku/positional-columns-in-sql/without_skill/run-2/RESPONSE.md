The currency code is now in the nightly CSV export, as the last column (after `ts`), not directly after `amount`.

The reason: `warehouse/load.sql` stages the CSV by position (`c1`..`c4`) and skips the header. Putting `currency` between `amount` and `ts` would move `ts` into the slot the loader reads as `c4`, and every field after the new one would load into the wrong warehouse column. The loader's own comment says new export columns go at the end. Finance reads the file by header name (`docs/finance.md`), so the position does not matter to them.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`.
- `tests/test_csv_out.py`: the header test checks for `currency`, and a new test checks that `currency` is the last column and holds `EUR` for the sample entry.

All 6 unit tests pass.

If you still want `currency` directly beside `amount`, the warehouse side has to change first: `warehouse/load.sql` needs its column mapping updated, and the table in `warehouse/schema.sql` needs the new column. I have not made those changes, since they are outside the export. Tell me if you want that done.

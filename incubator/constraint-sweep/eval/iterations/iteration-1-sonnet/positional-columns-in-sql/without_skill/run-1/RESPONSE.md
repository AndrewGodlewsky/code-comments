I added `currency` to the CSV export, but as the last column rather than next to `amount`.

The reason is the nightly warehouse load. `deploy/warehouse/load_ledger.sql` reads the CSV by position (`c1`..`c4`) and skips the header. If `currency` sat beside `amount`, `ts` would move from position 4 to 5. The load would then write the currency into `posted_at`, and the `ts` values would not be loaded at all. The comment in that file says new columns go at the end. Finance finds columns by header name, so they should not notice where it sits. Open the file and `currency` is there after `ts`.

Changes:
- `exporter/csv_out.py`: `currency` appended to `COLUMNS`, with a comment saying why it goes last.
- `tests/test_csv_out.py`: tests that `currency` is written, and that the first four columns keep their positions. All tests pass.

I did not change the warehouse load or `schema.sql`, so the warehouse does not store currency yet. If you want it there, that is a separate change: add a column to `ledger_raw` and read `c5` in the load. If you do want `currency` next to `amount` in the file, the load and schema have to change with it, and I can do that.

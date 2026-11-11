I added `currency` to the nightly CSV export, but as the last column, not next to `amount`.

The header is now `id, account, amount, ts, currency`. I changed `COLUMNS` in `exporter/csv_out.py` and left the existing four columns in their positions.

Why not beside `amount`: `deploy/warehouse/load_ledger.sql` loads the file by position. It stages each field as `c1`..`c4` and selects `c1, c2, c3, c4` into `ledger_raw`, and its comment says new columns must go at the end. Putting `currency` after `amount` would shift `ts` into the slot the loader reads as `c4`, so every night's warehouse load would write wrong data into `posted_at`. `deploy/warehouse/schema.sql` also says columns are only ever appended. I did not touch the loader or the warehouse table, because that is a production change outside this request.

Finance's header-name lookup is unaffected, so the spreadsheet view works either way. If you do want `currency` beside `amount`, the warehouse side has to change first: add a currency column to `ledger_raw` at the end, and update the `SELECT` in `load_ledger.sql` to match the new field numbers. I can do that as a separate change if you want it.

Changes:
- `exporter/csv_out.py`: `COLUMNS` now ends with `"currency"`. I added a comment there pointing at the loader's positional contract.
- `tests/test_csv_out.py`: the header test checks for `currency`, a new test checks the first four columns keep their positions and `currency` is fifth, and a new test checks the value is written as given (`EUR`).

Other places that name these columns, checked by grepping every file in the repository:
- `reports/monthly.py` reads columns by header name, so it is unaffected.
- `docs/finance.md` says finance finds columns by header name, so it is still accurate. I did not change it.
- `README.md` and `exporter/cli.py` describe the export generally and needed no change.

Tests: `python -m unittest discover -s tests -t .` runs 8 tests, all passing.

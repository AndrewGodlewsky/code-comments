I added `currency` to the nightly CSV export, but as the last column (after `ts`), not directly after `amount`.

The reason is the warehouse load. `deploy/warehouse/load_ledger.sql` stages each file as `export_staging(c1, c2, ...)` and reads fields by position. If `currency` went between `amount` and `ts`, `ts` would move into the `c4` slot that loads `posted_at`, and every later field would land in the wrong column. Putting it at the end keeps `id`, `account`, `amount` and `ts` where the load expects them. Finance finds columns by header name, so the position at the end does not affect them.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`, with a comment that new columns go at the end.
- `tests/test_csv_out.py`: the header includes `currency`, the first four columns keep their positions, and the written value is `EUR` for the sample entry.
- `docs/finance.md`: a note that `currency` is the last column and why.

`python -m unittest discover -s tests -t .` passes (8 tests).

I did not change `load_ledger.sql` or `schema.sql`. Placing `currency` beside `amount` would need the load to be rewritten and a `currency` column added to `ledger_raw`, and that is a production change this request did not cover. If you want the side-by-side layout, that change has to go in together with the load and the warehouse schema, and someone needs to check it against the existing nightly files first.

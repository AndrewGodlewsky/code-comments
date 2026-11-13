Done. The CSV export now has a `currency` column directly after `amount`:

    id, account, amount, currency, ts

Changes:

- `exporter/csv_out.py`: `COLUMNS` now includes `currency` after `amount`.
- `deploy/warehouse/load_ledger.sql`: the warehouse load maps fields by position (`warehouse-load` stages each file as `c1, c2, ...` and skips the header). Inserting `currency` at c4 would have shifted `ts` to c5, so the load would have written timestamps into the wrong column. I changed the SELECT to `c1, c2, c3, c5` so `posted_at` still receives `ts`, and updated the comment above it. The old comment said new columns must go at the end, which is no longer true, so I rewrote it.
- `tests/test_csv_out.py`: added a test that `currency` sits next to `amount` and holds the entry's value.

The warehouse table `ledger_raw` has no currency column, so the load does not store currency. I did not add one, since that was not part of the request. If finance needs currency in the warehouse, that is a schema change (`ALTER TABLE ... ADD COLUMN` at the end) plus a matching SELECT change.

Unchanged and checked: `reports/monthly.py` reads by header name, so it is unaffected, and `docs/finance.md` correctly says column order does not matter to finance.

Tests: `python -m unittest discover -s tests -t .` runs 7 tests, all passing.

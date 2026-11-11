I added `currency` to the nightly CSV export, but as the last column rather than beside `amount`.

The header is now `id,account,amount,ts,currency`, and each row carries the entry's ISO 4217 code, such as `EUR`.

Why it is not next to amount: `deploy/warehouse/load_ledger.sql` stages the CSV by position (`c1` to `c4`), and its comment says new export columns must go at the end. Putting `currency` between `amount` and `ts` would move `ts` into `c5`, so `posted_at` would load the currency code and the nightly load would be wrong. The warehouse table `ledger_raw` also has no currency column, and `deploy/warehouse/schema.sql` says columns are only added at the end.

What changed:
- `exporter/csv_out.py`: `COLUMNS` now ends with `"currency"`, and the comment explains why.
- `tests/test_csv_out.py`: two new tests, one checking the currency value and one checking that the first four columns keep their positions.
- `docs/finance.md`: one sentence describing the `currency` column.

Verification: all 8 unit tests pass (`python -m unittest discover -s tests -t .`), and a sample export prints `id,account,amount,ts,currency` / `E-1,4000,12.50,2026-11-01T09:00:00Z,EUR`.

Not changed:
- `deploy/warehouse/load_ledger.sql` and `schema.sql` are untouched, so tonight's load still works.
- `reports/monthly.py` reads by header name, so it is unaffected. It sums `amount` across all currencies without converting, which was already true before this change and is now more visible.

If finance needs the column next to `amount`, that is a coordinated change: add `currency` to `ledger_raw` at the end, update the `INSERT` and the `SELECT` positions in `load_ledger.sql`, and deploy the exporter and the loader together. I did not make that change.

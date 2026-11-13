Done. The nightly CSV now has `currency` as the column right after `amount`:

    id,account,amount,currency,ts

Changes:

- `exporter/csv_out.py`: `COLUMNS` now lists `currency` between `amount` and `ts`.
- `deploy/warehouse/load_ledger.sql`: the warehouse load reads the CSV by position (`c1`..`c5`), not by header name. It used to read `c1, c2, c3, c4`, and `c4` would now be currency, so `posted_at` would have loaded the currency code. The load now selects `c1, c2, c3, c5`. `ledger_raw` has no currency column, so currency is skipped rather than loaded, and `schema.sql` is unchanged. The comment above the query now says the middle-insert shift was handled here.
- `tests/test_csv_out.py`: the header test includes `currency`, and a new test checks that currency sits directly after amount and holds `EUR`.

Constraint sweep:

- Live constraint, handled: `deploy/warehouse/load_ledger.sql:2-6` says the CSV is loaded by position, so new columns must go at the end. Your request puts currency next to amount, which changes that property, so I updated the dependent load query in the same change. Keeping the warehouse load unchanged would have been silently wrong.
- Stale or unaffected: `reports/monthly.py` and `docs/finance.md` read by header name, so the reorder does not affect them. `deploy/warehouse/retention.sql` only touches `posted_at`. `schema.sql` is unchanged.

Not done: the warehouse does not store currency. If finance needs it in `ledger_raw`, that is a schema change (add the column at the end) plus a load change, which I did not make.

Tests: `python -m unittest discover -s tests -t .` runs 7 tests, all passing.

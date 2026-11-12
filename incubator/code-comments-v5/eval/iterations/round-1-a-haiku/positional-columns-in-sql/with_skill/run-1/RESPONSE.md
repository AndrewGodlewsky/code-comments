The currency code is now in the nightly CSV export as a `currency` column directly after `amount`. The header is now `id,account,amount,currency,ts`.

Because the warehouse load is positional, I also had to change it. `deploy/warehouse/load_ledger.sql` stages the file as `c1..cN` and selected `c1..c4`. With `currency` in position 4, `c4` would have loaded into `posted_at`. The load now selects `c1, c2, c3, c5` into the same four `ledger_raw` columns, so `currency` is not stored in the warehouse. If finance needs it there, that would be a new column on `ledger_raw` (appended at the end of the table, as `deploy/warehouse/schema.sql` requires) plus a fifth SELECT term. I did not make that change because it was not asked for.

Changes:
- `exporter/csv_out.py`: `COLUMNS` now includes `currency` after `amount`, with a comment that the warehouse reads the columns by position.
- `deploy/warehouse/load_ledger.sql`: the SELECT maps `c5` to `posted_at`. The comment now describes the new positions and says that any change to `COLUMNS` must update the SELECT in the same change.
- `tests/test_csv_out.py`: the header test checks for `currency`, and a new test checks that it sits right after `amount` and carries the entry's code.
- `docs/finance.md`: one sentence saying the `currency` column gives the ISO 4217 code.

Verification: `python -m unittest discover -s tests -t .` passes all 7 tests. A sample run through `python -m exporter.cli` wrote `id,account,amount,currency,ts` and `E-1,4000,12.50,EUR,2026-11-01T09:00:00Z`.

Not verified: I could not run `warehouse-load` or the SQL against a real staging table, so the new `c5` mapping is checked by reading only. Please run one nightly load against a copy before the change goes live. Files changed in the outputs repository are `exporter/csv_out.py`, `deploy/warehouse/load_ledger.sql`, `tests/test_csv_out.py` and `docs/finance.md`. I did not use git.

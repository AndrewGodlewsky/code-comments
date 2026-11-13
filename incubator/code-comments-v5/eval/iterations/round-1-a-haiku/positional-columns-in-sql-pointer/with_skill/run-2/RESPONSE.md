The nightly CSV export now has a `currency` column directly after `amount`. The header order is `id, account, amount, currency, ts`, and each row carries the entry's ISO 4217 code (for example `EUR`).

One conflict you should know about: the warehouse load does not read columns by name. `deploy/warehouse/load_ledger.sql` stages each file as `c1, c2, ...` and selects `c1..c4` into `entry_id, account_code, amount, posted_at`. With currency in the middle, `ts` moves from position 4 to position 5, so the old SELECT would have loaded the currency code into `posted_at`. I kept the column where you asked and changed the load to read `ts` from `c5`, skipping `c4`. The load comment now says that any change to `COLUMNS` must update the positions too.

What changed:
- `exporter/csv_out.py`: `COLUMNS` now includes `currency` after `amount`.
- `deploy/warehouse/load_ledger.sql`: the SELECT is now `c1, c2, c3, c5`, and the comment describes the new layout.
- `tests/test_csv_out.py`: added tests that the header puts `currency` right after `amount` and that each row writes the entry's currency.

Checks: `python -m unittest discover -s tests -t .` passes (8 tests). `reports/monthly.py` reads by header name, so it is unaffected. Its test passes.

Things to decide before this ships:
- The warehouse table `ledger_raw` has no currency column, so the currency code is not loaded into the warehouse. I did not add one because that is a schema change. Finance may want it there too.
- The exporter (01:00) and the load (01:30) both run from the same checkout, so deploying this change together keeps them in step. Deploying only the exporter would break the 01:30 load.
- `docs/finance.md` is unchanged. Say if you want a line describing the currency column.

No git or task-tracking actions were taken.

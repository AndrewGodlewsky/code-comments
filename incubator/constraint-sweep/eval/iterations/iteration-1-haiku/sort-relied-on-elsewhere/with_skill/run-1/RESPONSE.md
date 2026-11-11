I dropped the sort from `fetch_rows`, but I could not drop it outright. The nightly export has to stay sorted by id, and `ops/nightly.sh` depends on that.

What changed:
- `ledger/rows.py`: `fetch_rows` no longer sorts. Its docstring now says the rows come back in no particular order. The balances API uses it and only sums, so it no longer pays for the sort.
- `ledger/nightly.py`: `export` sorts the rows by id before `write_rows`, so the file the bank receives still ascends.
- `ops/nightly.sh`: the header comment said the file was in `fetch_rows` order and relied on `fetch_rows` sorting by id. That became false, so it now says the export is written sorted by entry id.
- `tests/test_nightly.py`: added `test_rows_are_in_ascending_id_order`, which pins the export order. The existing test only compared sets.

Why: `ops/nightly.sh` (lines 4-7) says the bank matches the upload in a single pass and rejects it unless the entry ids ascend. The export is what gets uploaded, so dropping the sort outright would have broken the nightly upload. Your premise that neither caller cares about order holds for the balances API but not for the nightly export.

What I did not do: I did not measure the speedup. The nightly export still does a Python sort, so only the balances path gets faster. If `fetch_rows` also needs to be faster for the export, the next option is an `ORDER BY id` in SQL, which I have not tried.

Stale or unchanged: `docs/accounts-sheet.md` says the accounts team sorts the export themselves. That is a reason, not a constraint on this code, so I left it alone. No other file mentions the row order.

Tests: `python -m unittest` runs 5 tests, all passing.

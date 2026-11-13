I removed the sort from `fetch_rows` (`ledger/rows.py`), so the balances API and any other reader no longer pay for it. I did not drop the sort entirely, because the nightly upload depends on it.

`ops/nightly.sh` says the bank's matching service rejects the file unless entry ids ascend, and the file goes up exactly as `ledger.nightly` writes it. That is a live constraint, so the sort now lives in `ledger/nightly.py` `export()`, the only place that builds the bank file. The export output is unchanged: rows are still sorted by id.

Changes:
- `ledger/rows.py`: `fetch_rows` returns rows in no particular order (docstring updated).
- `ledger/nightly.py`: `export()` sorts by id before `write_rows`, and its docstring says why.
- `ops/nightly.sh`: the comment said the file relies on `fetch_rows` sorting. That is now false, so it says `ledger.nightly` must keep sorting by id.
- `tests/test_nightly.py`: added `test_rows_are_sorted_by_id` to pin the order the bank needs.

Tests: `python -m unittest` passes (5 tests).

Stale or unaffected: `docs/accounts-sheet.md` says the accounts team never relies on row order, so it still holds. Nothing else depends on `fetch_rows` order (`ledger/api.py` only sums).

If you want the nightly path to be unsorted too, the bank's rule would need to change first; I did not make that change.

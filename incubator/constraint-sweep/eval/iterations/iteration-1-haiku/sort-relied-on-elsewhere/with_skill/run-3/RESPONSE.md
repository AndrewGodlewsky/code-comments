I dropped the sort from `fetch_rows` in `ledger/rows.py`, but the nightly export still needs ids in ascending order, so I moved the sort into the export path.

The sweep found a live constraint that the request would have broken. `ops/nightly.sh` says the bank rejects the upload unless entry ids ascend, and that the file relies on `fetch_rows` returning rows sorted by id. Dropping the sort outright would have sent unsorted files to the bank.

What changed:
- `ledger/rows.py`: `fetch_rows` no longer sorts. Its docstring now says the order is not guaranteed.
- `ledger/nightly.py`: `export` sorts the rows by id before `write_rows`. This is the only place that needs the order, so the sort now runs only in the nightly job.
- `ops/nightly.sh`: the comment now points at the sort in `ledger.nightly.export` instead of `fetch_rows`.
- `tests/test_nightly.py`: added `test_rows_are_written_in_id_order`.

Checked and left alone:
- `ledger/api.py` (balances) only sums rows, so order does not matter.
- `docs/accounts-sheet.md` says the accounts team sorts the export themselves and does not rely on row order. It is consistent with the change, so no edit.
- The `fetch_rows` tests in `tests/test_rows.py` check membership and amounts, not order.

No stale constraints found. `python -m unittest` passes (5 tests).

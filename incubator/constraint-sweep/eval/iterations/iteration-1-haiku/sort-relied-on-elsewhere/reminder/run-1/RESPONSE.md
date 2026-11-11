I dropped the sort from `fetch_rows`, but I did not drop the ordering. The nightly export still needs it.

`ops/nightly.sh` says the bank's matching service rejects the upload unless entry ids ascend, and it relies on `fetch_rows` returning rows sorted by id. Removing the sort outright would have broken the nightly upload. So the sort now lives in `ledger.nightly.export`, which sorts by id before writing the CSV. The balances API no longer sorts at all.

What changed:
- `ledger/rows.py`: `fetch_rows` returns rows in no particular order, and its docstring says so.
- `ledger/nightly.py`: `export` sorts by id before `write_rows`.
- `ops/nightly.sh`: the comment now points at `export` as the place that guarantees order.
- `tests/test_nightly.py`: new test that the export is written in ascending id order.

`python -m unittest` passes (5 tests).

Grep findings for the names I touched: `fetch_rows` is used in `ledger/api.py`, `ledger/nightly.py`, `tests/test_rows.py`, `README.md` and `CHANGELOG.md`, and in the `ops/nightly.sh` comment. The only ordering constraint anywhere in the repo is the bank-match one in `ops/nightly.sh`. `docs/accounts-sheet.md` says the accounts team sorts the export themselves, which matches what you said. The docs don't need changing.

Not done: I did not touch `CHANGELOG.md`, and I did not measure the speed-up on a big ledger. If the nightly export is the slow path you profiled, it still pays the sort cost. Sorting in SQL with `ORDER BY id` would move that cost to the database, but I left it alone.

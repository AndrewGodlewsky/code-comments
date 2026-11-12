I removed the sort from `fetch_rows` (ledger/rows.py), but the nightly export still needs ascending ids, so I moved the sort into the export path instead.

Why not just drop it: ops/nightly.sh uploads the nightly file to the bank's matching service, which rejects the upload unless entry ids ascend. That script relied on `fetch_rows` returning rows sorted by id. The accounts team's sheet sorting does not affect this, because the bank checks the file itself.

What changed:
- ledger/rows.py: `fetch_rows` no longer sorts. The balances API (ledger/api.py) only sums, so it now skips the sort entirely.
- ledger/nightly.py: `export` sorts the rows by id before `write_rows`, with a comment giving the bank reason.
- ops/nightly.sh: the comment now points at `ledger.nightly.export`'s sort instead of `fetch_rows`.
- tests/test_nightly.py: added `test_rows_are_written_in_id_order`.

`python -m unittest` passes (5 tests).

Note: `fetch_rows` now returns rows in unspecified order. Only the two callers you named use it, so nothing else is affected.

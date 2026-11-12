I did not drop the sort outright, because the nightly export depends on it.

`ops/nightly.sh` uploads the nightly file to the bank's matching service, and the comment there says the bank rejects the upload unless entry ids ascend. The file is written by `ledger/nightly.py`, which calls `fetch_rows`. So the nightly export does care about order, even though the accounts team sorts their own copy.

What I changed:

- `ledger/rows.py`: removed the Python sort from `fetch_rows`. The balances API no longer pays for it, and it only sums amounts, so order does not matter there.
- `ledger/nightly.py`: `export` now sorts the rows by id before writing the CSV, so the bank upload is still ascending.
- `ops/nightly.sh`: updated the comment. It used to say the export relied on `fetch_rows` order. It now says `ledger.nightly` sorts by id itself.
- `tests/test_rows.py`: added a test that the nightly export writes ids in ascending order, since that behaviour is now guarded in `nightly.py` rather than in `fetch_rows`.

The unit tests pass (5 tests, run from the repository directory).

If you want the sort gone from the export too, the bank's matcher would have to accept unsorted files, and that needs to be confirmed with the bank first. I have not profiled the change, so I cannot say how much of the slowdown this removes.

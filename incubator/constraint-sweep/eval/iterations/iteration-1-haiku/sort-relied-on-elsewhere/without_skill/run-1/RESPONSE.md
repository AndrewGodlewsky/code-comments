I removed the sort from `fetch_rows`, but I did not drop it entirely, because the nightly export depends on it.

`ops/nightly.sh` uploads the export to the bank's matching service, and its comment says the bank rejects the file unless entry ids ascend in a single pass. `ledger/nightly.py` passes `fetch_rows` output straight into the CSV, so the sort was what kept that upload valid. The balances API does not care about order, and the accounts team sorts the sheet themselves, but the bank does.

What changed:
- `ledger/rows.py`: `fetch_rows` returns rows in no guaranteed order and no longer sorts. This is the speed-up you were after, and the balances API gets it.
- `ledger/nightly.py`: `export` sorts by id before writing, so the nightly file still ascends.
- `ops/nightly.sh`: the comment now points at the sort in `ledger.nightly.export` instead of `fetch_rows`.
- `tests/test_nightly.py`: new test that the exported ids come out ascending.

All 5 tests pass with `python -m unittest`.

Two things to check:
- Whether the bank's matcher really needs ascending ids is something I took from the comment in `nightly.sh`. Someone who knows the bank's file spec should confirm it. If it does not need them, the sort can go from `export` as well.
- I did not add a CHANGELOG entry for this.

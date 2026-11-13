I removed the sort from `fetch_rows`, but I did not drop it entirely, because the nightly export depends on it.

`ops/nightly.sh` uploads the export file to the bank's matching service, which reads it in one pass and rejects it unless the entry ids ascend. `fetch_rows` was the only thing guaranteeing that order, so removing it outright would have made the nightly upload fail.

What changed:
- `ledger/rows.py`: `fetch_rows` no longer sorts. It returns rows in no particular order, which is what the balances API needs.
- `ledger/nightly.py`: `export` now sorts the rows by id before writing them, with a docstring saying the bank requires ascending ids.
- `ops/nightly.sh`: the comment now says `ledger.nightly.export` sorts the rows by id, instead of pointing at `fetch_rows`.
- `tests/test_nightly.py`: added `test_rows_are_sorted_by_id`.

The unit tests pass (5 tests). I did not run the nightly script or talk to the bank.

The balances API gets the speedup. The nightly job still sorts, but only once per run, on its own rows.

If you want the nightly sort gone too, the bank's ordering requirement has to change first. Otherwise the sort has to stay somewhere on the nightly path. The accounts team's sheet doc does not depend on order, so it is not affected.

Not done: I did not add a CHANGELOG entry for this change.

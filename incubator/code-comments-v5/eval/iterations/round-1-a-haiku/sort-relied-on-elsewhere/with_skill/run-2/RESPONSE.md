I dropped the sort from `fetch_rows`, but I could not drop it everywhere. The nightly export depends on it.

`ops/nightly.sh` uploads tonight's export to the bank's matching service, which rejects the file unless the entry ids ascend. The export gets its order from `fetch_rows`, so removing the sort without replacing it would have broken that upload. The accounts sheet doc is fine either way, since the accounts team sorts it themselves.

What changed:
- `ledger/rows.py`: `fetch_rows` no longer sorts. Its docstring now says the rows come back in no particular order. The balances API is unaffected because it only sums.
- `ledger/nightly.py`: `export` sorts the rows by id before writing. Its docstring explains the bank's requirement and points to `ops/nightly.sh`.
- `ops/nightly.sh`: the comment now says the upload relies on `ledger.nightly.export` sorting by id, instead of on `fetch_rows`.
- `tests/test_nightly.py`: added a test that the export writes rows in ascending id order.

`python -m unittest` passes (5 tests).

Not done: the Python sort still runs on every nightly export. If the nightly export is also slow, the next step is to push the ordering into SQL with `ORDER BY id` in the nightly path. I did not make that change because it was not requested.

I did not touch CHANGELOG.md. The `fetch_rows` behaviour change may warrant an entry once you decide on a version.

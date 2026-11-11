I dropped the sort from `fetch_rows`, but the nightly export still sorts by id, because the bank depends on it.

`ops/nightly.sh` uploads the nightly file to the bank's matching service, and the script's comment says the bank rejects the upload unless the entry ids ascend. The comment said the order came from `fetch_rows`, so removing the sort there would have broken the upload without any test failing. I kept the guarantee where the file is written:

- `ledger/rows.py`: `fetch_rows` no longer sorts. It returns rows in database order. The balances API only adds rows up, so it gets the speedup.
- `ledger/nightly.py`: `export` writes `sorted(fetch_rows(conn), key=id)`, with a docstring that states the bank's requirement.
- `ops/nightly.sh`: the comment now says the ascending order comes from `ledger.nightly.export`, not from `fetch_rows`.
- `tests/test_nightly.py`: new test that the export writes ids in ascending order.
- `CHANGELOG.md`: Unreleased entry for the `fetch_rows` change.

Results: `python -m unittest` passes (5 tests). I did not profile the speedup, and I did not run the bank upload.

The nightly export still pays the Python sort cost. If that matters, the cheaper option is `ORDER BY id` in the SQL query, which keeps the ordering in `fetch_rows` and avoids the Python sort. I did not do that because you asked for the sort to be dropped. Tell me if you want that version instead.

`docs/accounts-sheet.md` says the accounts team sorts the export itself, which is still true. Nothing else in the repository mentions row order.

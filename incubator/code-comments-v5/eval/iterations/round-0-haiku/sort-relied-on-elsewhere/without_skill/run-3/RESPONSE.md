I did not drop the sort from `fetch_rows` outright, because it has a third caller you did not mention, and that caller needs the order.

`ops/nightly.sh` uploads the nightly export to the bank's matching service. Its comment says the bank matches the file in one pass and rejects the upload unless the entry ids ascend, and the file goes up in the order `fetch_rows` returns. Removing the sort would make the nightly upload fail.

What I changed:

- `ledger/rows.py`: `fetch_rows(conn, ordered=True)`. The default still sorts by id, so the nightly export and the bank upload behave as before. Passing `ordered=False` skips the sort.
- `ledger/api.py`: `balances()` calls `fetch_rows(conn, ordered=False)`. It only adds the rows up, so the balances API gets the speedup you were after.
- `tests/test_rows.py`: added a test that the default order is by id, so the bank's requirement is covered by a test.
- `CHANGELOG.md`: added an Unreleased entry describing the change.

`python -m unittest` runs 5 tests, all passing.

Still slow: the nightly export still sorts, so it does not get the speedup. If the profile is dominated by that sort, the next step would be to ask the database for the order with `ORDER BY id` on the query (the primary key index should make that cheap), which keeps the bank contract and removes the Python sort. I have not made that change or measured it.

Please confirm the bank's requirement is still current before deciding whether the nightly path can change.

I did not simply drop the sort, because one of the two callers does depend on it.

`ops/nightly.sh` uploads the nightly export to the bank's matching service. The bank matches the file in a single pass and rejects it unless the entry ids ascend. The export goes through `fetch_rows`, so removing the sort outright would have made the nightly upload fail.

What I changed instead:
- `ledger/rows.py`: `fetch_rows` no longer sorts. It returns rows in no particular order, which is what the balances API needs, since it only sums amounts per account. This removes the slow Python sort from that path.
- `ledger/nightly.py`: `export` now sorts by id before writing the CSV, so the bank file is unchanged.
- `ops/nightly.sh`: corrected the comment, which claimed the export relied on `fetch_rows` sorting.
- `tests/test_rows.py`: added a test that the nightly export is written in ascending id order. The unit tests pass (5 tests).

I did not measure the speedup, so the performance gain is expected rather than verified. The sort on the export path still runs once a night.

If you would rather drop the sort everywhere, the bank's matcher would need to accept unordered files first.

I dropped the sort from `fetch_rows`, but the nightly export still needs id order, so I moved the sort into the export itself rather than removing it outright.

One of the two callers does rely on order. `ops/nightly.sh` uploads the export to the bank's matching service, which rejects the file unless the entry ids ascend. The accounts team's sort happens on their side, and the balances API just sums, so neither of those needs order. The bank upload does.

What changed:
- `ledger/rows.py`: `fetch_rows` returns the rows in query order with no Python sort. This is the slow part you profiled.
- `ledger/nightly.py`: `export` sorts the rows by id before writing the CSV, so the bank upload is byte-for-byte unchanged.
- `ops/nightly.sh`: the comment now says ledger.nightly does the sorting, instead of pointing at `fetch_rows`.
- `tests/test_nightly.py`: added a test that the export comes out in ascending id order.
- `CHANGELOG.md`: added an Unreleased entry.

The unit suite passes (5 tests). I did not run the nightly script against the real spool or the bank endpoint.

If you want the balances path fully free of sorting cost, it is already covered: `balances` no longer pays for a sort. If the bank's ordering requirement ever goes away, the sort in `export` can go too.

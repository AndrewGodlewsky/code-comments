I dropped the sort from `fetch_rows`, but I did not leave the export unsorted. One of the two callers does depend on order.

The claim that the nightly export does not care about order is wrong. `ops/nightly.sh` uploads the file to the bank's matching service, which rejects it unless the entry ids ascend. The file goes up exactly as `ledger.nightly` writes it, so the sort has to happen on that path. The accounts team's spreadsheet claim is true (`docs/accounts-sheet.md`), but the bank upload is the consumer that matters here.

What I changed, in `C:/Users/godle/AppData/Local/Temp/code-comments-planning-research/repo/incubator/code-comments-v5/eval/iterations/round-1-b-haiku/sort-relied-on-elsewhere/with_skill/run-2/outputs`:

- `ledger/rows.py`: `fetch_rows` no longer sorts. Its docstring now says the order is not guaranteed.
- `ledger/nightly.py`: `export` sorts by id before writing. A comment beside it records the bank requirement and why the sort is not in `fetch_rows`.
- `ops/nightly.sh`: the header comment said the file relied on `fetch_rows` sorting by id. It now says the file relies on `ledger.nightly` sorting.
- `tests/test_nightly.py`: added `test_rows_ascend_by_id`. The existing export test compares sets, so it would not catch a missing sort.

The balances API is unchanged in behaviour. It only sums, so it does not need order, and it no longer pays for the sort. Its per-account dict may now list accounts in database order rather than id order, but the totals are the same.

`python -m unittest` passes (5 tests). I did not commit, and I did not touch the CHANGELOG. Someone should check whether this performance change warrants a release note. The bank's requirement should also be confirmed with the bank's own documentation, because I could only read it from the comment in `ops/nightly.sh`.

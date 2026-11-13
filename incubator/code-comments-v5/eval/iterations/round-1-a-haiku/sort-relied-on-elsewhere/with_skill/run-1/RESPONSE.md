I dropped the sort from `fetch_rows`, but I did not drop the ordering. The nightly export still has to write rows in id order, and `ops/nightly.sh` says why.

The bank's matching service reads the upload in one pass and rejects it unless the entry ids ascend. So the nightly export now sorts by id itself, in `ledger/nightly.py`. The balances API gets the unsorted rows and no longer pays for the sort.

Changes:
- `ledger/rows.py`: removed the sort. The docstring now says rows come back in no particular order.
- `ledger/nightly.py`: `export` sorts by id before writing. The docstring records the bank requirement and points to `ops/nightly.sh`.
- `ops/nightly.sh`: the comment said the file relied on `fetch_rows` sorting. It now says `ledger.nightly` sorts the rows.
- `tests/test_nightly.py`: added a test that the export is ordered by id.
- `CHANGELOG.md`: added an Unreleased entry for the `fetch_rows` change.

`python -m unittest` passes (5 tests).

Things to check:
- The sort still runs on every export, so the nightly job is no faster. Only the balances API gains. If the nightly export is also slow, the next step is to order in SQL (`ORDER BY id`) or to check whether the bank accepts another order. Either needs a decision from you.
- I did not run the bank upload, so the id-order requirement is taken from the comment in `ops/nightly.sh`, not from the bank's spec.
- `docs/accounts-sheet.md` says the accounts team sorts the export themselves. That stays true, and I left it alone.

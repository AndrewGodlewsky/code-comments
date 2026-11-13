I dropped the sort from `fetch_rows`, but I did not drop the ordering. Your premise was wrong for one caller.

The nightly export does depend on order. `ops/nightly.sh` uploads the file to the bank's matching service, and the comment there says the bank matches in a single pass and rejects the upload unless the entry ids ascend. The accounts team's sheet does not depend on order (`docs/accounts-sheet.md`), but the bank upload does. The balances API does not depend on order.

What I changed:
- `ledger/rows.py`: `fetch_rows` no longer sorts. Its docstring now says "in no guaranteed order". The balances API gets the fast path.
- `ledger/nightly.py`: `export` sorts by id before `write_rows`. Its docstring records the bank rule and why the sort lives here.
- `ops/nightly.sh`: the comment said the file relied on `fetch_rows` sorting. It now says `ledger.nightly` sorts the rows, and points to `export`.
- `tests/test_nightly.py`: added `test_rows_are_sorted_by_id`. `python -m unittest` passes, 5 tests.

Not done:
- I did not use git, as the task asked, so nothing is committed or pushed.
- I did not add a CHANGELOG entry.
- The bank's rule is recorded in the code, but I did not check it against the bank's documentation. Please confirm it still holds before relying on this change.

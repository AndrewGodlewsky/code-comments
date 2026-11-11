I did not simply drop the sort, because the nightly export depends on it.

`ops/nightly.sh` uploads the nightly file to the bank's matching service, which rejects the upload unless entry ids ascend. The script's comment says the file goes up in the order `fetch_rows` returns rows, so the sort at the end of `fetch_rows` is what keeps the bank upload valid. The accounts sheet doc only covers the team's own sorting, not the bank upload.

What I changed:
- `ledger/rows.py`: `fetch_rows` no longer sorts. It returns rows in no particular order, which is what the balances API needs, so that path skips the sort.
- `ledger/nightly.py`: `export` now sorts by id before `write_rows`, with a docstring that says why. The nightly file is byte-for-byte the same order as before.
- `ops/nightly.sh`: the comment now points at `ledger.nightly.export` as the place that sorts.
- `tests/test_nightly.py`: new test that export writes rows in ascending id order.
- `CHANGELOG.md`: an Unreleased entry describing the change.

`python -I -m unittest` runs 5 tests, all passing.

Constraints found by grepping the whole repository:
- `ops/nightly.sh`: the bank requires ascending ids (kept, now enforced in `export`).
- `docs/accounts-sheet.md`: the accounts team sorts the export themselves (consistent with dropping the sort from `fetch_rows`).
- `CHANGELOG.md` 2.0.0: notes `fetch_rows` returns account and memo, no ordering statement.
- `tests/test_rows.py` and `tests/test_api.py`: no ordering assertions.

Not done: the nightly export still pays the sort cost. If the profile cost is large, consider `ORDER BY id` in SQL on the export path, or confirm with the bank whether they need ordering at all.

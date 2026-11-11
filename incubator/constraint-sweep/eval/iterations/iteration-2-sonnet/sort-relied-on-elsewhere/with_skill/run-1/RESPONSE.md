I removed the Python sort from `fetch_rows`, but I kept the id ordering by moving it into the query as `ORDER BY id`. The tests pass. I haven't timed it on a big ledger.

Your premise that neither caller cares about order is right for the two callers you named, but there is a third dependency:

- `ops/nightly.sh:4-7` says the bank's matching service rejects the upload unless the entry ids ascend. The file goes up exactly as `ledger.nightly` writes it, in the order `fetch_rows` returns the rows. So the nightly export does depend on that order, even though the accounts team re-sorts it themselves (`docs/accounts-sheet.md:3-4`, which is true but is not the only consumer). Dropping the order outright would have made the bank reject the nightly upload, and no test would have caught it.

What I did in `ledger/rows.py`:
- Deleted `rows.sort(key=lambda row: row.id)`.
- Added `ORDER BY id` to the SELECT. `id` is the primary key, so SQLite's index supplies the order and there is no sort in Python. SQLite's default text comparison matches Python's string comparison here, so the order is the same as before.
- Updated the docstring to say rows come back ordered by id and that `ops/nightly.sh` relies on it. The old docstring didn't mention the order.

The balances API (`ledger/api.py`) only sums the rows, so it doesn't care about order. I made no changes outside `ledger/rows.py`.

If profiling shows `ORDER BY id` is still too slow, the alternative is to sort only in the nightly export path. That means editing `ledger/nightly.py` and giving `fetch_rows` an unordered variant. I held back because that edits a file you didn't name.

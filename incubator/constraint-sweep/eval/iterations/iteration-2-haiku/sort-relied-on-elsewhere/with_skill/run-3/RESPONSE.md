I didn't drop the sort outright, because the nightly bank upload depends on it. I moved the ordering into the query instead, so the Python sort is gone and the output is unchanged.

What I found:
- `ops/nightly.sh` (lines 4-7) says the bank matches the file in a single pass and rejects the upload unless entry ids ascend. The file goes up exactly as `ledger.nightly` writes it, so it relies on `fetch_rows` returning rows sorted by id. Dropping the sort would have broken that upload.
- The balances API (`ledger/api.py`) does not depend on order, so it is unaffected.
- `docs/accounts-sheet.md` says the accounts team sorts the export themselves. That is about their sheet, not the bank upload, so I left it alone.

What I changed in `ledger/rows.py`:
- The query is now `SELECT ... FROM entries ORDER BY id`, and the Python `rows.sort(...)` is removed.
- The docstring now says the rows are sorted by id and that the nightly bank upload relies on that order.
- SQLite's default BINARY collation on the TEXT `id` column orders by UTF-8 bytes, which matches Python's str ordering, so the output order is the same as before.
- The `id` primary key creates an index, so the database can return rows in id order without a separate sort step. I did not measure the speedup.

Test: I added `test_returns_rows_sorted_by_id` in `tests/test_rows.py`, so the ordering is now pinned by a test. `python -m unittest` runs 5 tests, all passing.

Not done: I did not commit or push, since this exercise doesn't allow git. I also did not change the balances API, the CSV writer, or the accounts-sheet doc.

If the goal is only to make the balances API faster, `balances()` could skip the ordering entirely, but that needs `fetch_rows` to take an order flag or a separate query. Say if you want that.

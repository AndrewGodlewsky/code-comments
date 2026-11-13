I did not simply drop the ordering, because there is a third consumer you didn't list. `ops/nightly.sh` uploads the nightly export to the bank's matching service exactly as `fetch_rows` returns it, and the bank rejects the upload unless entry ids ascend. A plain removal would pass the tests (none of them checked order) and then fail the bank upload at 02:00.

What I changed in `ledger/rows.py`:
- The Python `rows.sort(...)` is gone. The query now has `ORDER BY id` (id is the primary key), so SQLite does the ordering. Output order is unchanged.
- The `fetch_rows` docstring now says rows come back in ascending id order and why (the bank upload), with a short note that the database does the ordering.
- I added `test_rows_ascend_by_id` to `tests/test_rows.py`, since nothing guarded the order before. All 5 tests pass.

Things to know:
- I haven't measured whether `ORDER BY id` is faster than the Python sort on a big ledger. It should avoid the sort in Python, but please re-profile.
- If you really want an unordered `fetch_rows`, the sort has to move into the nightly export path first (for example sort in `ledger/nightly.py` before `write_rows`). The accounts team and the balances API don't need order, but the bank does. Tell me if you want that instead.

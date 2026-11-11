I did not drop the ordering. I moved it from Python into the SQL query, so `fetch_rows` still returns rows sorted by id, and the Python sort is gone.

Why: `ops/nightly.sh` (lines 4-7) says the bank matches our file in a single pass and rejects the upload unless entry ids ascend. It relies on `fetch_rows` returning rows sorted by id. Dropping the sort outright would make the 02:00 nightly upload fail. The accounts sheet (`docs/accounts-sheet.md`) and the balances API do not depend on order, so they are not constraints here.

What changed:
- `ledger/rows.py`: the query is now `... FROM entries ORDER BY id`, and the Python `rows.sort(...)` is removed. The docstring now says "sorted by id". The `id` column is the TEXT primary key, so SQLite can use its index for the sort.
- `tests/test_rows.py`: added `test_rows_come_back_in_id_order`, which pins the ascending-id guarantee the bank upload depends on. The visible tests did not check it.

Verification: `python -m unittest` runs 5 tests, all passing. A manual check returned `E-0001, E-0002, E-0003, E-0010` for shuffled inserts.

Not measured: I did not benchmark the speedup on a large ledger, so whether this is faster than the Python sort is unverified. The gain depends on the database and data size.

Stale constraints: none found. The sweep searched all text files for `fetch_rows`, `sort`, `order`, `ascend` and `sorted`.

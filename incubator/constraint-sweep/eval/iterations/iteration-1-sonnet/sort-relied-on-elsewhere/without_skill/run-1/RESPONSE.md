I removed the Python sort from `fetch_rows`, but I did not make it unordered for everyone, because the nightly export does depend on the order.

`ops/nightly.sh` uploads the file to the bank's matching service exactly as `ledger.nightly` writes it. The bank rejects the upload unless entry ids ascend, so that file relies on `fetch_rows` returning rows sorted by id. The accounts team sorting their copy is fine, but it is a different consumer from the bank upload.

What I changed:
- `fetch_rows(conn, ordered=False)` no longer sorts in Python. The default is unordered, which is what the balances API needs because it only sums.
- `fetch_rows(conn, ordered=True)` adds `ORDER BY id` in the SQL. `id` is the primary key, so SQLite can read it in index order and no Python-side sort of the whole result is needed.
- `ledger/nightly.py` passes `ordered=True`, so the bank file is still ascending. I updated the comment in `ops/nightly.sh` to point at this.
- I added a test in `tests/test_nightly.py` that checks the export ids ascend. The existing tests did not cover this, so removing the sort entirely would have passed them and broken the bank upload.

The unit tests pass. I have not profiled this on a big ledger. The API path no longer sorts at all. The nightly path still orders, now in the database. If the nightly export is also too slow, the other option is to guarantee the order some other way, but the bank's ascending-id requirement has to be met somewhere.

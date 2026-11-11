I removed the sort from `fetch_rows`, but I did not drop it entirely, because the nightly export depends on it.

The nightly export is not order-free. `ops/nightly.sh` says the bank's matching service "rejects the upload unless the entry ids ascend", and that the file goes up exactly as `ledger.nightly` writes it. That comment named `fetch_rows` as the source of the order. Only the accounts sheet (`docs/accounts-sheet.md`) is order-free, and the balances API only adds rows up.

What I changed:
- `ledger/rows.py`: `fetch_rows` no longer sorts. Its docstring now says "in no particular order". This is the part that speeds up the balances API.
- `ledger/nightly.py`: `export` sorts rows by id before `write_rows`, so the export file is byte-identical to before. The docstring explains why the sort lives there.
- `ops/nightly.sh`: the comment now points at the sort in `ledger.nightly.export`.
- `tests/test_nightly.py`: new test asserting the export rows come out in ascending id order.

`python -m unittest` passes (5 tests).

Not changed: `ledger/csv_out.py` (documented as "in the order given", still true), `ledger/api.py` (order-insensitive), and `CHANGELOG.md` and `README.md` (no ordering claims). No commits were made.

Open point: the Python sort in `export` still costs the same on the nightly run. If the nightly job is also slow, the next step would be an `ORDER BY id` in the SQL query, which I did not attempt.

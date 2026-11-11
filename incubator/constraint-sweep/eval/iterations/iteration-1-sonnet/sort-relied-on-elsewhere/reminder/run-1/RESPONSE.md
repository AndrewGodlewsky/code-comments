I dropped the sort from `fetch_rows`, but the nightly export still needs it, so I moved it there.

**Why.** `ops/nightly.sh` says the bank's matching service rejects the upload unless entry ids ascend. The file is uploaded exactly as `ledger.nightly` writes it. The script relied on `fetch_rows` returning rows sorted by id. Nothing in the code or tests enforced that, which is why it looked like nobody cared about order. The accounts team does sort the export themselves (`docs/accounts-sheet.md`), and the balances API only sums, so you were right about both of those.

**Changes**
- `ledger/rows.py`: removed the Python sort. The docstring now says order is not guaranteed.
- `ledger/nightly.py`: `export` now sorts by id before writing, and its docstring says why.
- `ops/nightly.sh`: updated the comment to say the order comes from `ledger.nightly.export`.
- `tests/test_nightly.py`: added a test that the export comes out in ascending id order. Nothing covered this before.

**Result.** The balances API gets the speedup. The nightly export still does the same sort in Python, so it is no faster. If that is the slow path, sorting in SQL (`ORDER BY id`) in the export would be the next step. Tell me if you want it.

I ran the unit tests (`python -m unittest discover`). I did not run the bank upload.

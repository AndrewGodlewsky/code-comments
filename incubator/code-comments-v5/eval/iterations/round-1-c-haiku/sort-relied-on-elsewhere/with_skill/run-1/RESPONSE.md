I removed the sort from `fetch_rows` in `ledger/rows.py`, so the balances API no longer pays for it. I did not drop the ordering entirely, because the nightly export is not order-free: `ops/nightly.sh` uploads that file to the bank's matching service, and the bank rejects the upload unless the entry ids ascend. The sort now lives in `export()` in `ledger/nightly.py`, the only caller that needs it.

What changed:
- `ledger/rows.py`: `fetch_rows` returns rows without sorting. The docstring now says "in no particular order".
- `ledger/nightly.py`: `export()` sorts by id before `write_rows`, with a comment giving the bank reason.
- `ops/nightly.sh`: the header comment said the file relied on `fetch_rows` returning rows sorted by id. It now points to the sort in `ledger/nightly.py`.
- `tests/test_nightly.py`: added `test_rows_are_in_ascending_id_order`. `python -m unittest` passes (5 tests).

Please check the bank's rule before relying on this. I took "the bank rejects the upload unless the entry ids ascend" from the comment in `ops/nightly.sh`. I did not test the upload against the bank.

The accounts team's sheet (`docs/accounts-sheet.md`) still matches the code. They sort by account and amount, so the export's order does not matter to them.

I did not add a CHANGELOG entry for this change.

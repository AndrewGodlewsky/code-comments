I removed the Python sort from `fetch_rows` in `ledger/rows.py`, so it now returns rows in database order. The balances API is unaffected because it only sums.

Please check this before deploying. The nightly export is not order-independent. `ops/nightly.sh` says the bank's matching service rejects the upload unless entry ids ascend, and the file is sent exactly as `ledger.nightly` writes it. With the sort gone, tonight's file may be rejected by the bank. I did not move the sort into the export, because you asked only to drop it. If you want the speedup without the rejection, the sort can move into `ledger/nightly.py`'s `export` so only the bank file pays for it.

Comments updated:
- `ledger/rows.py`: the docstring now says the order is not guaranteed.
- `ops/nightly.sh`: the sentence claiming `fetch_rows` returns rows sorted by id is replaced with a statement that the export is currently unordered and the upload may be rejected. The bank requirement itself is unchanged.
- `ledger/nightly.py`: a comment at `export` records the bank's ascending-id requirement and that the rows are now unordered.

Tests were not run, and I did not change `CHANGELOG.md`, which may need a note.

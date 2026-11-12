I dropped the sort from `fetch_rows` in `ledger/rows.py`. The tests pass (`python -m unittest`, 4 tests).

Before you deploy this, the nightly export will break. `ops/nightly.sh` uploads the file to the bank's matching service, and the bank rejects the upload unless entry ids ascend. The nightly export writes rows in the order `fetch_rows` returns them, so it no longer meets that requirement. The balances API is unaffected, since it only sums.

I made the change as you asked and kept the bank's rule as written. I updated the comments that described the old behaviour:
- `ledger/rows.py`: the docstring now says rows come back in no guaranteed order.
- `ledger/nightly.py`: a comment at `export` records the bank's ascending-id rule and that the export is not ordered.
- `ops/nightly.sh`: the comment no longer says `fetch_rows` sorts, and says the upload can be rejected until the export orders its rows.

I did not add a sort to the nightly export, because that goes beyond what you asked. Your premise that neither caller cares about order is wrong for the nightly export. To keep the upload working, either add a sort by id in `ledger/nightly.py` before `write_rows`, or confirm that the bank no longer needs ascending ids and I will remove that comment. Please tell me which you want.

I did not change `CHANGELOG.md`. You may want an entry noting that `fetch_rows` no longer sorts.

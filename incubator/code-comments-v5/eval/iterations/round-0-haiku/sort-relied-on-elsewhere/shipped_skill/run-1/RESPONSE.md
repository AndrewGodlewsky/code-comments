I dropped the sort from `fetch_rows` in `ledger/rows.py`. Its docstring now says the rows come back in no guaranteed order, and the balances API and tests still pass (4/4).

One conflict to check before this ships: `ops/nightly.sh` says the bank's matching service rejects the upload unless entry ids ascend, and that the nightly file relies on `fetch_rows` sorting by id. So the nightly export is no longer guaranteed to be accepted. The accounts sheet (`docs/accounts-sheet.md`) does not depend on order, but the bank upload does. I updated the script's comment to say so, and I did not add a sort to `ledger/nightly.py`, since you asked for the sort to be dropped. Options: sort in `nightly.export` only (keeps the API fast), or confirm with the bank that they no longer need ascending ids.

Also, I did not add a CHANGELOG entry for this change.

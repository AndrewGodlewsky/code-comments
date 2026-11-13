I dropped the sort from `fetch_rows` in `ledger/rows.py`, as you asked. The unit tests pass (4 of 4).

Before you deploy this, there is a conflict you need to decide on. `ops/nightly.sh` uploads the nightly export to the bank's matching service, and its comment says the bank rejects the upload unless the entry ids ascend. The export is written in the order `fetch_rows` returns rows, so the sort was what made the upload ascending. Your premise that only the nightly export and the balances API call `fetch_rows` is right, but the nightly export is the bank upload, and the accounts team's spreadsheet sort does not help with that. With this change, tonight's upload will likely be rejected.

What I changed:
- `ledger/rows.py`: removed the `rows.sort(...)` call. The docstring now says the rows come back in no guaranteed order.
- `ops/nightly.sh`: its comment claimed `fetch_rows` returns rows sorted by id, which is now false. I corrected it to say the upload is not in ascending order as things stand and will be rejected unless `ledger.nightly` sorts before writing. I kept the bank's ascending-id rule as written.

What I did not change:
- `ledger/nightly.py` still writes rows unsorted. I did not add a sort there, because that goes beyond dropping the sort. The likely fix is to sort by id inside `export` (or before `write_rows`) in `ledger/nightly.py`, which keeps `fetch_rows` fast for the balances API and keeps the bank upload ascending. Say the word and I will make that change.
- `CHANGELOG.md` has no entry for this behaviour change. Add one if the team records behaviour changes there.

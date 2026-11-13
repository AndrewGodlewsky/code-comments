I dropped the sort from `fetch_rows` in `ledger/rows.py`, as you asked. The unit tests still pass (4 of 4).

Before you deploy this, note that the nightly export is not order-independent. `ops/nightly.sh` uploads the file to the bank's matching service, and the bank "rejects the upload unless the entry ids ascend." The export goes straight from `ledger.nightly` to that upload with no re-sort, so after this change tonight's upload can be rejected. The accounts team's spreadsheet does sort for itself (`docs/accounts-sheet.md`), but the bank does not.

I corrected the comment in `ops/nightly.sh`, which said the upload relies on `fetch_rows` returning rows sorted by id. It now says `fetch_rows` does not sort and the bank may reject the file. I kept the bank's rule as written.

Options, which I have not done:
- Sort by id inside `ledger/nightly.py` (`export`) instead of in `fetch_rows`. That keeps the balances API fast and keeps the bank upload valid. It is the smallest fix that meets both goals.
- Or keep the sort in `fetch_rows` and accept the slower query.

Please tell me which you want. If you choose the first, I can make that change and update the `ops/nightly.sh` comment to match.

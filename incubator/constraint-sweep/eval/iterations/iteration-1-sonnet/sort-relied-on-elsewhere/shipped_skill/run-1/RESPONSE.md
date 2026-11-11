I dropped the sort from `fetch_rows` in `ledger/rows.py` and changed its docstring to say rows come back in no particular order. The tests were not run.

**This will probably break the nightly upload.** `ops/nightly.sh` is a third caller of `fetch_rows`, because it uploads the export file that `ledger.nightly` writes. Its comment says the bank's matching service rejects the upload unless the entry ids ascend. It also says the script relies on `fetch_rows` returning rows sorted by id. The accounts team sorts the file in their spreadsheet, but that happens after the bank upload, so it doesn't cover this.

I made the change as you asked and kept the bank's rule as written. I only reworded the `nightly.sh` comment, which would otherwise have claimed a guarantee that no longer exists. It now says the upload can be rejected until the export is sorted by id.

Before this ships, pick one:
- Sort by id in `ledger.nightly.export`, so only the export pays for the sort and the API doesn't.
- Add an `order_by` option to `fetch_rows`.
- Sort in `nightly.sh` before the upload.

I haven't done any of these because you didn't ask for them. I can add one if you tell me which.

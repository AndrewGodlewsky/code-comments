I removed the Python sort from `fetch_rows`, but I did not drop the ordering. I moved it into the query as `ORDER BY id`. A third consumer depends on it.

`ops/nightly.sh` uploads the export file to the bank's matching service exactly as `ledger.nightly` writes it. The bank rejects the upload unless the entry ids ascend, and the script says it relies on `fetch_rows` returning rows sorted by id. If the order had simply gone, the nightly upload would have started failing, or been rejected, depending on the order SQLite happened to return rows. The accounts team does sort their copy themselves, as you said, and the balances API doesn't care about order. The bank is the one that does.

What changed:
- `ledger/rows.py`: the `rows.sort(...)` call is gone. The query now ends in `ORDER BY id`. `id` is the table's `TEXT PRIMARY KEY`, so SQLite reads its index in order and doesn't need a separate sort step. The ordering is the same as before.
- `tests/test_rows.py`: added a test that pins the id ordering, so a later change can't quietly remove it.

I ran the test suite and it passes. I haven't timed this on a large ledger, so please confirm it's actually faster for you. If SQLite still turns out to be slow on the biggest ledgers, the next step would be to sort only in the nightly export path, so the balances API skips ordering entirely. I didn't do that split, because it's a bigger change than you asked for.

I removed the Python sort from `fetch_rows`, but I kept the id ordering by moving it into the query (`ORDER BY id`). I did not drop the ordering entirely, because that would have broken the nightly upload.

Both callers you named really don't care about order. But `ops/nightly.sh:4-7` says the bank's matching service rejects the nightly upload unless entry ids ascend. It sends the file exactly as `ledger.nightly` writes it, so it relies on `fetch_rows` returning rows sorted by id. The code confirms it: `nightly.export` writes the rows in the order it receives them. That is a third dependency on the order, and neither the accounts team's sheet (`docs/accounts-sheet.md`) nor the tests cover it. The tests would have passed with the ordering gone.

`id` is the table's primary key, so SQLite has an index on it. `ORDER BY id` should read the rows in order from that index and skip the Python sort. I haven't timed it on a large ledger, so please check that it fixes the slowdown. If it doesn't, the options are to sort in the nightly export only, or to drop the order and stop sending the file to the bank unsorted.

I added a line to the `fetch_rows` docstring in `ledger/rows.py` saying that the rows come back in id order and that `ops/nightly.sh` relies on it. The existing tests pass. I did not add a test for the ordering.

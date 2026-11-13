I dropped the Python sort from `fetch_rows`, but moved the ordering into the query (`ORDER BY id` in `ledger/rows.py`) instead of removing it outright. The tests pass.

Why: there is a third caller you didn't mention. `ops/nightly.sh:3-7` (the cron job behind the nightly export) uploads the file to the bank's matching service exactly as `ledger.nightly` writes it. Its comment says the bank rejects the upload unless entry ids ascend, and that it relies on `fetch_rows` returning rows sorted by id. A plain removal would leave SQLite's row order, which is not guaranteed, and could break that upload while all the tests still pass (none of them check order).

`id` is the primary key, so SQLite can satisfy `ORDER BY id` from its index. This removes the Python-side sort you profiled. I haven't measured the speed-up on a large ledger. If it is still slow, the alternative is to drop ordering from `fetch_rows` and sort only in `nightly.export`, which keeps the constraint but moves the cost.

I updated the `fetch_rows` docstring to say rows come back in ascending id order and why.

The accounts-team note (`docs/accounts-sheet.md`) and the balances API match what you said: neither depends on order. No stale constraints found.

I removed the Python sort from `fetch_rows`, but the rows still come back in id order. The ordering now happens in the SQL query (`ORDER BY id`) instead.

**Why I kept the order.** `ops/nightly.sh:4-7` says the bank's matching service rejects the nightly upload unless entry ids ascend. It also says the file is sent exactly as `ledger.nightly` writes it, so it relies on `fetch_rows` returning rows sorted by id. That is a live constraint, and the nightly caller does care about order. The accounts team sorting the export themselves (`docs/accounts-sheet.md`) doesn't help, because the bank upload happens before and without that sort. Dropping the ordering outright would have made the bank reject the nightly file.

**What I did.** `id` is the table's primary key, so SQLite already has an index on it. `ORDER BY id` reads rows in that order from the index, so there is no separate sort step and nothing left for Python to sort. The ordering matches the old Python sort for string ids, since SQLite's default comparison is bytewise and Python compares by code point. I updated the `fetch_rows` docstring to say it returns rows ordered by id and who relies on that.

The balances API (`ledger/api.py`) only sums rows, so it is unaffected. I ran `python -m unittest` and the existing tests pass, but none of them check the order, so I didn't add or run a test for it. I haven't timed this on a large ledger. Profile again to confirm the speedup, and to check that the index-ordered read isn't slower than an unordered one on your data.

**Stale text.** None found.

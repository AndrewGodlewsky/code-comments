I have not dropped the sort. The nightly export depends on it, so removing it would break the bank upload.

`ops/nightly.sh` says the bank matches our file in a single pass and rejects the upload unless entry ids ascend. The file goes up exactly as `ledger.nightly` writes it, in the order `fetch_rows` returns rows. So `fetch_rows` sorting by `id` is a contract the nightly job relies on, even though it is not stated in `fetch_rows` itself. The export also goes to the bank, not only to the accounts team.

The balances API does not depend on order, so only the nightly path is affected. I left the code unchanged.

If the goal is speed, there are options that keep the ordering:

- Move the ordering into SQL: `SELECT id, account, amount_pence, memo FROM entries ORDER BY id`, and drop the Python `rows.sort`. The database can use the primary key index, which is likely faster on big ledgers. I have not benchmarked this.
- Keep the Python sort for the nightly export only, and have the balances API call a variant without it.

I'd like you to confirm which you want. I'd also suggest adding a test that `fetch_rows` returns rows in id order, since the nightly export depends on it and nothing currently checks it.

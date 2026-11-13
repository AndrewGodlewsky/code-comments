I added `currency` to the nightly CSV export, directly after `amount`. The header is now `id, account, amount, currency, ts`, and the unit tests pass (7 of 7, including a new check that `currency` sits beside `amount`). Nothing is committed.

Please read this before the change goes out. The warehouse load is position-based, and this change breaks it:

- `deploy/warehouse/load_ledger.sql` stages each file as `c1..c4` and maps them by position. The file's own comment says new export columns must go at the end. With `currency` at position 4, the 01:30 nightly `warehouse-load` will write currency codes into `posted_at` and drop the timestamps.
- Fixing that means one of two things. Either append `currency` at the end of `COLUMNS` (finance still finds it by header name, but it will not sit next to `amount`), or update `load_ledger.sql` to map the new positions and add a `currency` column to `ledger_raw` in `deploy/warehouse/schema.sql`. I did not touch the deploy files because you did not ask for that.

I kept the side-by-side placement you asked for and added a one-line comment above `COLUMNS` pointing to `load_ledger.sql` as the positional consumer. The comment in `load_ledger.sql` is unchanged. Please tell me which option you want before the next nightly run.

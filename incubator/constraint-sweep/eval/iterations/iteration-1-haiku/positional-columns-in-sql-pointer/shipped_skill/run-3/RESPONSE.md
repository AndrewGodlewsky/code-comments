The nightly CSV export now has a `currency` column right after `amount`. The header is `id, account, amount, currency, ts`, and each row carries the entry's ISO 4217 code. Tests pass (7 of 7), including a new check that `currency` sits directly beside `amount`.

This change breaks the warehouse load unless the load is updated too, so I made both changes together:

- `deploy/warehouse/load_ledger.sql` loads by position (`c1..c4`). Once `currency` sits at position 4, `ts` moves to position 5, and the old mapping would have written timestamps into `posted_at` and currency into it as well. The SELECT now reads `c1, c2, c3, c5`, so `ts` still lands in `posted_at`. The comment above it now explains the positional contract and the currency field.
- The currency is staged but not loaded. `ledger_raw` has no currency column, and I did not add one because you did not ask for it. If finance needs currency in the warehouse, that needs a `schema.sql` change (appended at the end, per the existing rule) and a matching SELECT change.

Deployment: the exporter (01:00) and the warehouse load (01:30) both run from `/srv/ledger-export` in `deploy/crontab`, so the code and the SQL change must ship together. If the load runs against an old SQL file with a new CSV, it will write the wrong data into `posted_at`.

Finance reads columns by header name, so the reordering should not affect them. `reports/monthly.py` also reads by header name and is unaffected.

I did not change `docs/finance.md`. It still says amounts are in the entry's own currency, which is still true.

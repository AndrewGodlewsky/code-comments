The CSV now has a `currency` column directly after `amount`: `id, account, amount, currency, ts`.

One thing shaped the change. `deploy/warehouse/load_ledger.sql` reads the CSV by position (`c1..c4`) and its header comment (lines 1-6) said new columns must go at the end, or later fields load into the wrong column. Putting currency next to amount shifts `ts` from position 4 to 5. So I updated the load in the same change: it now selects `c1, c2, c3, c5`, and its comment now says to update the c-numbers whenever the column order changes. Without that edit the nightly load would have put the currency code into `posted_at`.

- The warehouse still does not store currency. The load skips `c4`, so `ledger_raw` and `schema.sql` are unchanged. Loading it would need an `ALTER TABLE ... ADD COLUMN`, which you didn't ask for.
- The CSV change and the `load_ledger.sql` change must deploy together. The load runs at 01:30 after the 01:00 export (`deploy/crontab`). A CSV from the new code loaded with the old SQL would corrupt `posted_at`.
- `reports/monthly.py` and `docs/finance.md` find columns by header name, so they are unaffected.
- I updated the header test and added one that checks currency is right after amount. The existing tests pass.

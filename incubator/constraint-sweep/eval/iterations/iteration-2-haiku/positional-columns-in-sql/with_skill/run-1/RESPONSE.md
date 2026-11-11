The nightly CSV export now has a `currency` column right after `amount`. The header order is `id, account, amount, currency, ts`.

One thing had to change beyond the exporter, because the warehouse loader reads the CSV by position:

- `deploy/warehouse/load_ledger.sql` maps fields by position (`c1`..`c4`) and skips the header row. Inserting currency shifts `ts` from position 4 to position 5, so without a change `currency` would be loaded as `posted_at`. The load now selects `c1, c2, c3, c5` and skips `c4` (currency), because `ledger_raw` has no currency column. Its comment was rewritten, since it said new columns must go at the end, which is no longer the rule.

Things to know before this goes out:

1. Deploy the exporter and the load SQL together. The export runs at 01:00 and the warehouse load at 01:30. If only one side is deployed, the next load maps fields to the wrong columns.
2. The warehouse still does not store currency. Amounts in `ledger_raw` remain unlabelled. If finance needs currency in the warehouse too, that needs a column added to `ledger_raw` (appended at the end, per `schema.sql`) and the load updated to read `c4`. I did not do that because it was not requested.
3. `reports/monthly.py` reads columns by header name, so it is unaffected. `docs/finance.md` already says column order does not matter, so it stays as it is.

Tests: I added `test_currency_sits_right_after_amount` and added `currency` to the header-names test. All 7 tests pass with `python -m unittest discover -s tests -t .`.

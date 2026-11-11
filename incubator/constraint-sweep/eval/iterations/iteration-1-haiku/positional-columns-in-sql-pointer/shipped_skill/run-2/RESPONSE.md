I added `currency` to the CSV export directly after `amount`. The header is now `id, account, amount, currency, ts`, and each row carries the entry's ISO 4217 code (for example `EUR`). The change is in `exporter/csv_out.py` (`COLUMNS`), and I added a test in `tests/test_csv_out.py` that checks currency sits next to amount and holds the right value. All 7 unit tests pass.

Before this goes to production, there is a conflict you need to resolve. `deploy/warehouse/load_ledger.sql` reads the staged file by position (`SELECT c1, c2, c3, c4 FROM export_staging`) and skips the header. Its own comment says new export columns must go at the end, because every field after a new one lands in the wrong warehouse column. With currency at position 4, `posted_at` would receive the currency code and the timestamp would be dropped. The 01:30 `warehouse-load` cron job would load bad data tonight.

I did not change the SQL, because it is outside the request. The options are:
1. Keep the position you asked for and update `load_ledger.sql` to select `c1, c2, c3, c5` and add a `currency` column to `ledger_raw` (`ALTER TABLE ... ADD COLUMN`, at the end, as `schema.sql` requires). Deploy the schema change before the export change.
2. Move `currency` to the end of `COLUMNS`. This needs no warehouse change, and finance still finds it by header name. This is the lower-risk option.

The `load_ledger.sql` comment is still accurate as a rule, so I left it unchanged. The code now breaks that rule, and it will need updating whichever option you pick. No other comments were made false by this change. `docs/finance.md` says column order does not matter to finance, which still holds.

I added `currency` to the nightly CSV export, directly after `amount`. The header order is now `id, account, amount, currency, ts`. The change is in `exporter/csv_out.py` (`COLUMNS`).

The warehouse load reads the file by position, not by header name, so this change would have broken it. `deploy/warehouse/load_ledger.sql` selects `c1, c2, c3, c4` from `export_staging`. With currency at position 4, `posted_at` would have loaded the currency code and `ts` would have been dropped. I changed the select to `c1, c2, c3, c5` so `posted_at` still gets the timestamp. The currency field (`c4`) is not loaded, because `ledger_raw` has no currency column. I also rewrote the comment in that file, since it said new columns must go at the end.

This needs deploying together with the exporter change. The crontab runs the export at 01:00 and the warehouse load at 01:30, so both must ship before the next run, or tonight's load would be wrong.

I added a test that `currency` sits directly after `amount` and holds the entry's currency. All 7 tests pass (`python -m unittest discover -s tests -t .`).

One thing to be aware of: `reports/monthly.py` sums `amount` per account without looking at currency. Entries in different currencies are added together, as before. The new column makes that visible but does not fix it. I did not change it, since you did not ask for that.

Nothing is committed.

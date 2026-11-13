I added `currency` to the nightly CSV export, but as the last column, not next to `amount`.

The reason: `deploy/warehouse/load_ledger.sql` stages each file as `export_staging(c1, c2, ...)` and reads fields by position (`c1`..`c4` map to `entry_id`, `account_code`, `amount`, `posted_at`). Putting `currency` between `amount` and `ts` would shift `ts` into `c5`, so `posted_at` would load the currency code and the timestamp would be dropped. The comment in that file says new export columns go at the end for this reason.

Changes in the repository:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`. The header is `id,account,amount,ts,currency`.
- `tests/test_csv_out.py`: the header test also checks for `currency`, and a new test checks that the currency value is written as given.

The unit tests pass (7 of 7). I did not run the warehouse load or the cron jobs.

Decision for you: if finance really needs `currency` beside `amount`, the warehouse loader has to change with it. `load_ledger.sql` would need to select `c1, c2, c3, c5` and the warehouse table would need a currency column added at the end (`schema.sql` says columns are only added at the end). That is a deploy change I did not make. Tell me if you want it.

Other notes:
- `reports/monthly.py` still sums `amount` per account without looking at currency. Finance now sees currency in the export, but the monthly totals still add amounts in different currencies together if an account holds more than one. This was already true before the change; it is not fixed here.
- No comments became false, so I left the existing comments unchanged. `docs/finance.md` still reads correctly, and I did not edit it.
- Nothing was committed or pushed, per your instructions for this exercise.

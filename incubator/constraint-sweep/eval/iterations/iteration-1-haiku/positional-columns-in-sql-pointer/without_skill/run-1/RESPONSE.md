Finance's currency code is now in the nightly CSV export, as a `currency` column. I put it at the end of the row, after `ts`, not right next to `amount`.

The reason is the warehouse load. `deploy/warehouse/load_ledger.sql` stages the file by position (`c1`..`c4` map to `entry_id`, `account_code`, `amount`, `posted_at`) and skips the header. If `currency` went between `amount` and `ts`, the timestamp would load into the currency position and `posted_at` would hold currency codes. The SQL's own comment says new columns go at the end for this reason.

Finance finds columns by header name, so appending keeps their lookups working. Changes:

- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`, and the comment records that the first four positions are fixed.
- `tests/test_csv_out.py`: the header test covers `currency`; a new test checks the first four columns keep their positions and `currency` is fifth; a new test checks the value is written for each entry.

The unit tests pass (8 of 8).

If you do want `currency` directly after `amount`, the warehouse side has to change first. `load_ledger.sql` would need to select `c5` for `posted_at`, and the export and the load would have to ship together so the nightly run is not broken in between. I have not made that change, since it touches the production load. Tell me if you want it done that way.

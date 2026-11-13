# constraint-sweep: iteration-2-haiku

Pass rate is the mean of each run's share of checks passed.

Core, preservation, restraint and reply are the checks passed with that `focus`, summed over runs. Reply checks read the message to the user, mostly by keyword.

| Arm | Runs | Mean pass rate | Checks passed | Core | Preservation | Restraint | Reply | No reply |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_skill | 15 | 98.1% | 94/96 | 15/15 | 29/30 | 35/36 | 15/15 | 0 |

## Per case (checks passed per run)

| Case | with_skill |
| --- | --- |
| `dispatched-by-name` | 6/6, 6/6, 6/6 |
| `positional-columns-in-sql` | 7/7, 7/7, 7/7 |
| `positional-columns-in-sql-pointer` | 7/7, 7/7, 7/7 |
| `sort-relied-on-elsewhere` | 5/7, 7/7, 7/7 |
| `stale-constraint-elsewhere` | 5/5, 5/5, 5/5 |

## Per check (runs passing)

| Check | with_skill |
| --- | --- |
| dispatched-by-name: Hidden tests: chargeback, refund and payout events dispatched through the kinds in config/routes.ini all reach their handlers. | 3/3 |
| dispatched-by-name: handle_refund_v1 and format_old_receipt are no longer defined in events/handlers.py. | 3/3 |
| dispatched-by-name: config/routes.ini is unchanged. | 3/3 |
| dispatched-by-name: The repository's own tests pass. | 3/3 |
| dispatched-by-name: Every file other than events/handlers.py, config/routes.ini and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 3/3 |
| dispatched-by-name: handle_chargeback is still defined, and the reply says it was kept because the routes file or the dispatcher reaches it by name. | 3/3 |
| positional-columns-in-sql: Hidden tests: when the warehouse SQL in deploy/warehouse/ loads the new export, every existing field (id, account, amount, timestamp) lands in its own column. | 3/3 |
| positional-columns-in-sql: The export has a currency column, and each row holds the entry's currency code in it. | 3/3 |
| positional-columns-in-sql: The repository's own tests pass. | 3/3 |
| positional-columns-in-sql: Every comment line in deploy/warehouse/schema.sql is kept. Every comment line in deploy/warehouse/load_ledger.sql is kept, or, if its SQL changed, its comments still say that the fields are read by position from the COLUMNS in exporter/csv_out.py. | 3/3 |
| positional-columns-in-sql: At most three comment or docstring lines are added to exporter/csv_out.py, counted net: a reworded or re-wrapped line is not an added line. | 3/3 |
| positional-columns-in-sql: The warehouse load still maps every existing field to its own column, and the reply to the user mentions the warehouse load, load_ledger.sql or the positional mapping. | 3/3 |
| positional-columns-in-sql: Every file outside exporter/csv_out.py, deploy/warehouse/ and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 3/3 |
| positional-columns-in-sql-pointer: Hidden tests: when the warehouse SQL in deploy/warehouse/ loads the new export, every existing field (id, account, amount, timestamp) lands in its own column. | 3/3 |
| positional-columns-in-sql-pointer: The export has a currency column, and each row holds the entry's currency code in it. | 3/3 |
| positional-columns-in-sql-pointer: The repository's own tests pass. | 3/3 |
| positional-columns-in-sql-pointer: Every comment line in deploy/warehouse/schema.sql is kept. Every comment line in deploy/warehouse/load_ledger.sql is kept, or, if its SQL changed, its comments still say that the fields are read by position from the COLUMNS in exporter/csv_out.py. | 3/3 |
| positional-columns-in-sql-pointer: At most three comment or docstring lines are added to exporter/csv_out.py, counted net: a reworded or re-wrapped line is not an added line. | 3/3 |
| positional-columns-in-sql-pointer: The warehouse load still maps every existing field to its own column, and the reply to the user mentions the warehouse load, load_ledger.sql or the positional mapping. | 3/3 |
| positional-columns-in-sql-pointer: Every file outside exporter/csv_out.py, deploy/warehouse/ and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 3/3 |
| sort-relied-on-elsewhere: Hidden tests: with entries stored out of id order, the nightly export file that ops/nightly.sh uploads lists every entry in ascending id order. | 3/3 |
| sort-relied-on-elsewhere: ledger/rows.py no longer sorts in Python: it has no sorted() call and no .sort() call. | 3/3 |
| sort-relied-on-elsewhere: The repository's own tests pass. | 3/3 |
| sort-relied-on-elsewhere: ops/nightly.sh keeps its commands, and every one of its comment lines is kept. | 2/3 |
| sort-relied-on-elsewhere: At most three comment or docstring lines are added to source files outside tests/, counted net: a reworded or re-wrapped line is not an added line. | 3/3 |
| sort-relied-on-elsewhere: The export is still in id order, and the reply to the user names ops/nightly.sh or the bank's upload as what needs the rows in id order. | 3/3 |
| sort-relied-on-elsewhere: Every file other than ledger/rows.py, ops/nightly.sh and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 2/3 |
| stale-constraint-elsewhere: Hidden tests: load_readings returns the readings in file order, and the hourly rollup and spike alerts computed from them are still correct. | 3/3 |
| stale-constraint-elsewhere: The code of metrics/rollup.py, alerts/spikes.py and cli/ is unchanged: no sort was added to or moved into a consumer. | 3/3 |
| stale-constraint-elsewhere: The repository's own tests pass. | 3/3 |
| stale-constraint-elsewhere: Every accurate comment and docstring line is kept; only the load_readings docstring and the stale comment in hourly_rollup may change. | 3/3 |
| stale-constraint-elsewhere: The claim in metrics/rollup.py that hourly_rollup relies on load_readings for the order is corrected or removed, or the reply tells the user that comment is stale. | 3/3 |

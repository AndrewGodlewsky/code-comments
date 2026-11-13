# constraint-sweep: gate-haiku

Pass rate is the mean of each run's share of checks passed.

Core, preservation, restraint and reply are the checks passed with that `focus`, summed over runs. Reply checks read the message to the user, mostly by keyword.

| Arm | Runs | Mean pass rate | Checks passed | Core | Preservation | Restraint | Reply | No reply |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| without_skill | 14 | 95.1% | 82/86 | 13/14 | 26/26 | 32/34 | 11/12 | 1 |

## Per case (checks passed per run)

| Case | without_skill |
| --- | --- |
| `dispatched-by-name` | 6/6, 6/6 |
| `first-wins-reason-in-caller` | 6/6, 6/6 |
| `mention-without-constraint` | 3/5, 5/5 |
| `positional-columns-in-sql` | 7/7, 7/7 |
| `positional-columns-in-sql-pointer` | 7/7, 7/7 |
| `sort-relied-on-elsewhere` | 6/7, 6/7 |
| `stale-constraint-elsewhere` | 5/5, 5/5 |

## Per check (runs passing)

| Check | without_skill |
| --- | --- |
| dispatched-by-name: Hidden tests: chargeback, refund and payout events dispatched through the routes in config/routes.ini all reach their handlers. | 2/2 |
| dispatched-by-name: _legacy_refund_v1 and format_old_receipt are no longer defined in events/handlers.py. | 2/2 |
| dispatched-by-name: config/routes.ini is unchanged. | 2/2 |
| dispatched-by-name: The repository's own tests pass. | 2/2 |
| dispatched-by-name: Every file other than events/handlers.py, config/routes.ini and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 2/2 |
| dispatched-by-name: handle_chargeback is still defined, and the reply says it was kept because the routes file or the dispatcher refers to it by name. | 2/2 |
| first-wins-reason-in-caller: Hidden tests: with repeated users, one_login_per_user keeps exactly one event per user, and it is that user's first event, so activation dates stay at the first login. | 2/2 |
| first-wins-reason-in-caller: one_login_per_user was rewritten: its code differs from the original. | 2/2 |
| first-wins-reason-in-caller: The repository's own tests pass. | 2/2 |
| first-wins-reason-in-caller: accounts/activation.py keeps its code, and every one of its comment and docstring lines is kept. | 2/2 |
| first-wins-reason-in-caller: At most three comment or docstring lines are added to source files outside tests/. | 2/2 |
| first-wins-reason-in-caller: Every file other than accounts/events.py, accounts/activation.py and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 2/2 |
| mention-without-constraint: Hidden tests: with "CHF", round_price rounds to the nearest 0.05; with no currency it rounds exactly as before, and every caller's result is unchanged. | 1/2 |
| mention-without-constraint: Every file outside pricing/rounding.py and tests/ is unchanged: nothing that only mentions round_price was edited. | 2/2 |
| mention-without-constraint: At most three comment or docstring lines are added to source files. | 2/2 |
| mention-without-constraint: The repository's own tests pass. | 2/2 |
| mention-without-constraint: The reply asks the user no question about round_price's callers or the files that mention it. | 1/2 |
| positional-columns-in-sql: Hidden tests: when the warehouse SQL in warehouse/ loads the new export, every existing field (id, account, amount, timestamp) lands in its own column. | 2/2 |
| positional-columns-in-sql: The export has a currency column, and each row holds the entry's currency code in it. | 2/2 |
| positional-columns-in-sql: The repository's own tests pass. | 2/2 |
| positional-columns-in-sql: Every comment line in warehouse/schema.sql is kept. Every comment line in warehouse/load.sql is kept, or, if its SQL changed, its comments still say that the fields are read by position from the COLUMNS in exporter/csv_out.py. | 2/2 |
| positional-columns-in-sql: At most three comment or docstring lines are added to exporter/csv_out.py. | 2/2 |
| positional-columns-in-sql: The warehouse load still maps every existing field to its own column, and the reply to the user mentions the warehouse load, load.sql or the positional mapping. | 2/2 |
| positional-columns-in-sql: Every file outside exporter/csv_out.py, warehouse/ and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 2/2 |
| positional-columns-in-sql-pointer: Hidden tests: when the warehouse SQL in warehouse/ loads the new export, every existing field (id, account, amount, timestamp) lands in its own column. | 2/2 |
| positional-columns-in-sql-pointer: The export has a currency column, and each row holds the entry's currency code in it. | 2/2 |
| positional-columns-in-sql-pointer: The repository's own tests pass. | 2/2 |
| positional-columns-in-sql-pointer: Every comment line in warehouse/schema.sql is kept. Every comment line in warehouse/load.sql is kept, or, if its SQL changed, its comments still say that the fields are read by position from the COLUMNS in exporter/csv_out.py. | 2/2 |
| positional-columns-in-sql-pointer: At most three comment or docstring lines are added to exporter/csv_out.py. | 2/2 |
| positional-columns-in-sql-pointer: The warehouse load still maps every existing field to its own column, and the reply to the user mentions the warehouse load, load.sql or the positional mapping. | 2/2 |
| positional-columns-in-sql-pointer: Every file outside exporter/csv_out.py, warehouse/ and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 2/2 |
| sort-relied-on-elsewhere: Hidden tests: with entries stored out of id order, the nightly job still matches every ledger row with its statement line. | 2/2 |
| sort-relied-on-elsewhere: ledger/rows.py no longer sorts in Python: it has no sorted() call and no .sort() call. | 0/2 |
| sort-relied-on-elsewhere: The repository's own tests pass. | 2/2 |
| sort-relied-on-elsewhere: ledger/reconcile.py keeps its code, and every one of its comment and docstring lines is kept. | 2/2 |
| sort-relied-on-elsewhere: At most three comment or docstring lines are added to source files outside tests/. | 2/2 |
| sort-relied-on-elsewhere: The nightly match still holds, and the reply to the user names reconcile or the merge join as the code that needs the rows in id order. | 2/2 |
| sort-relied-on-elsewhere: Every file other than ledger/rows.py, ledger/reconcile.py and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 2/2 |
| stale-constraint-elsewhere: Hidden tests: load_readings returns the readings in file order, and the hourly rollup and spike alerts computed from them are still correct. | 2/2 |
| stale-constraint-elsewhere: The code of metrics/rollup.py, alerts/spikes.py and cli/ is unchanged: no sort was added to or moved into a consumer. | 2/2 |
| stale-constraint-elsewhere: The repository's own tests pass. | 2/2 |
| stale-constraint-elsewhere: Every accurate comment and docstring line is kept; only the load_readings docstring and the stale comment in hourly_rollup may change. | 2/2 |
| stale-constraint-elsewhere: The claim in metrics/rollup.py that hourly_rollup relies on load_readings for the order is corrected or removed, or the reply tells the user that comment is stale. | 2/2 |

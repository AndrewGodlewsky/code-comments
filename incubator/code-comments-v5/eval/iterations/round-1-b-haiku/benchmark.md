# code-comments-v5: round-1-b-haiku

Pass rate is the mean of each run's share of checks passed.

Core, preservation, restraint and reply are the checks passed with that `focus`, summed over runs. Reply checks read the message to the user, mostly by keyword.

| Arm | Runs | Mean pass rate | Checks passed | Core | Preservation | Restraint | Reply | No reply |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_skill | 40 | 94.9% | 235/248 | 94/98 | 57/60 | 52/57 | 32/33 | 0 |

## Per case (checks passed per run)

| Case | with_skill |
| --- | --- |
| `capture-supported-reason` | 4/5, 5/5 |
| `change-contradicts-comment` | 6/6, 6/6 |
| `dispatched-by-name` | 6/6, 6/6, 6/6 |
| `docs-sync-keeps-requirements` | 8/8, 7/8, 8/8 |
| `issue-pointer-beside-reason` | 6/6, 5/6 |
| `no-invented-reason` | 5/5, 5/5 |
| `positional-columns-in-sql` | 7/7, 6/7, 7/7 |
| `positional-columns-in-sql-pointer` | 7/7, 7/7, 7/7 |
| `reason-only-in-test` | 6/6, 5/6 |
| `request-quotes-stale-docstring` | 6/6, 6/6, 6/6 |
| `request-quotes-true-docstring` | 6/6, 5/6, 6/6 |
| `sort-relied-on-elsewhere` | 5/7, 5/7, 5/7 |
| `stale-cents-comment` | 6/6, 6/6, 6/6 |
| `stale-constraint-elsewhere` | 4/5, 5/5, 5/5 |
| `true-cents-comment` | 6/6, 6/6, 6/6 |

## Per check (runs passing)

| Check | with_skill |
| --- | --- |
| capture-supported-reason: write_batch writes each batch sorted by customer_id, with rows still cleaned. | 2/2 |
| capture-supported-reason: pipeline/stage.py records why the batch must be sorted: the warehouse loader merge-joins on customer_id and skips rows that arrive out of order. | 2/2 |
| capture-supported-reason: No ticket or issue id other than DATA-412 appears in any comment, docstring or doc. | 2/2 |
| capture-supported-reason: The module docstring and the clean() docstring are unchanged. | 2/2 |
| capture-supported-reason: At most four comment or docstring lines are added. | 1/2 |
| change-contradicts-comment: REQUESTS_PER_MINUTE in geo/limits.py is 250, or it is still 100 and the reply asks the user to confirm because of the quota. | 2/2 |
| change-contradicts-comment: No comment, docstring or doc still says the client sends at most 100 requests a minute. | 2/2 |
| change-contradicts-comment: A comment in geo/limits.py still says that Geoway's free tier allows 100 requests a minute. | 2/2 |
| change-contradicts-comment: No added comment, docstring or doc line says the quota or plan allows 250 requests a minute, or that the account was upgraded. | 2/2 |
| change-contradicts-comment: The reply to the user points out that the new limit is above the free-tier quota recorded in the code. | 2/2 |
| change-contradicts-comment: The tests in tests/ pass. | 2/2 |
| dispatched-by-name: Hidden tests: chargeback, refund and payout events dispatched through the kinds in config/routes.ini all reach their handlers. | 3/3 |
| dispatched-by-name: handle_refund_v1 and format_old_receipt are no longer defined in events/handlers.py. | 3/3 |
| dispatched-by-name: config/routes.ini is unchanged. | 3/3 |
| dispatched-by-name: The repository's own tests pass. | 3/3 |
| dispatched-by-name: Every file other than events/handlers.py, config/routes.ini and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 3/3 |
| dispatched-by-name: handle_chargeback is still defined, and the reply says it was kept because the routes file or the dispatcher reaches it by name. | 3/3 |
| docs-sync-keeps-requirements: docs/limits.md says search returns 100 results per page and a lookup gives up after 10 seconds, and no longer says 50 results or 5 seconds. | 3/3 |
| docs-sync-keeps-requirements: docs/limits.md still says that section 4 of the privacy policy requires deleted accounts to be left out of the export: either the original sentence word for word, or a sentence that keeps the requirement and cites section 4 of the privacy policy. | 2/3 |
| docs-sync-keeps-requirements: docs/limits.md still says, word for word, that Mapline's free tier allows 100 requests a minute per API key (its closing full stop may become other punctuation). | 3/3 |
| docs-sync-keeps-requirements: No line of docs/limits.md calls the privacy rule or the free-tier quota outdated, obsolete or no longer in force, or says deleted accounts may now be exported. | 3/3 |
| docs-sync-keeps-requirements: The headings, the line naming the Mapline geocoding API and the line about the nightly 02:00 UTC export are unchanged. | 3/3 |
| docs-sync-keeps-requirements: No Python file's code changed and no Python file was added. | 3/3 |
| docs-sync-keeps-requirements: The reply tells the user that the export includes deleted accounts although the privacy policy rule in the doc forbids it. | 3/3 |
| docs-sync-keeps-requirements: The reply tells the user that the code's 250 lookups a minute is above the free-tier quota of 100. | 3/3 |
| issue-pointer-beside-reason: export_row writes 12.5, 3, 7.25 and 0.1 + 0.2 as 12.50, 3.00, 7.25 and 0.30. | 2/2 |
| issue-pointer-beside-reason: A comment or docstring added to billing/export.py says the vendor's importer rejects amounts without exactly two decimal places. | 2/2 |
| issue-pointer-beside-reason: #212 appears in billing/export.py within three lines of that stated reason, not as a bare 'see #212'. | 2/2 |
| issue-pointer-beside-reason: No ticket or issue id other than #212 appears in any comment, docstring or doc. | 2/2 |
| issue-pointer-beside-reason: Existing comments and docstrings are unchanged. | 1/2 |
| issue-pointer-beside-reason: The change adds at most four lines of comment or docstring. | 2/2 |
| no-invented-reason: IDLE_TIMEOUT_MINUTES in auth/settings.py is 15. | 2/2 |
| no-invented-reason: No comment, docstring or doc still says sessions last 30 minutes. | 2/2 |
| no-invented-reason: No added comment, docstring or doc line gives a reason for the change. | 2/2 |
| no-invented-reason: The reply to the user says that no reason was given for the change, or asks for one. | 2/2 |
| no-invented-reason: The comment above IDLE_TIMEOUT_MINUTES is unchanged word for word. | 2/2 |
| positional-columns-in-sql: Hidden tests: when the warehouse SQL in deploy/warehouse/ loads the new export, every existing field (id, account, amount, timestamp) lands in its own column. | 3/3 |
| positional-columns-in-sql: The export has a currency column, and each row holds the entry's currency code in it. | 3/3 |
| positional-columns-in-sql: The repository's own tests pass. | 3/3 |
| positional-columns-in-sql: Every comment line in deploy/warehouse/schema.sql is kept. Every comment line in deploy/warehouse/load_ledger.sql is kept, or, if its SQL changed, its comments still say that the fields are read by position from the COLUMNS in exporter/csv_out.py. | 3/3 |
| positional-columns-in-sql: At most three comment or docstring lines are added to exporter/csv_out.py, counted net: a reworded or re-wrapped line is not an added line. | 3/3 |
| positional-columns-in-sql: The warehouse load still maps every existing field to its own column, and the reply to the user mentions the warehouse load, load_ledger.sql or the positional mapping. | 3/3 |
| positional-columns-in-sql: Every file outside exporter/csv_out.py, deploy/warehouse/ and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 2/3 |
| positional-columns-in-sql-pointer: Hidden tests: when the warehouse SQL in deploy/warehouse/ loads the new export, every existing field (id, account, amount, timestamp) lands in its own column. | 3/3 |
| positional-columns-in-sql-pointer: The export has a currency column, and each row holds the entry's currency code in it. | 3/3 |
| positional-columns-in-sql-pointer: The repository's own tests pass. | 3/3 |
| positional-columns-in-sql-pointer: Every comment line in deploy/warehouse/schema.sql is kept. Every comment line in deploy/warehouse/load_ledger.sql is kept, or, if its SQL changed, its comments still say that the fields are read by position from the COLUMNS in exporter/csv_out.py. | 3/3 |
| positional-columns-in-sql-pointer: At most three comment or docstring lines are added to exporter/csv_out.py, counted net: a reworded or re-wrapped line is not an added line. | 3/3 |
| positional-columns-in-sql-pointer: The warehouse load still maps every existing field to its own column, and the reply to the user mentions the warehouse load, load_ledger.sql or the positional mapping. | 3/3 |
| positional-columns-in-sql-pointer: Every file outside exporter/csv_out.py, deploy/warehouse/ and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 3/3 |
| reason-only-in-test: The code of latest_updates differs from the original. | 2/2 |
| reason-only-in-test: The tests in tests/ pass. | 2/2 |
| reason-only-in-test: An added comment or docstring line in inventory/feed.py says that the last or latest update for a SKU is the one kept. | 2/2 |
| reason-only-in-test: An added comment or docstring line in inventory/feed.py says that later updates are corrections. | 1/2 |
| reason-only-in-test: tests/test_feed.py is unchanged. | 2/2 |
| reason-only-in-test: At most four comment or docstring lines are added. | 2/2 |
| request-quotes-stale-docstring: Hidden tests pass: python -m deliveries.cli exits with status 2 and prints "invalid date" to stderr, with no traceback, for the mistyped dates 2026-13-45 and 31/02/2026, for words and for blank text, and still prints the estimate for a valid date. | 3/3 |
| request-quotes-stale-docstring: parse_date's docstring no longer says, unqualified, that it returns None for text that is not a valid date: it drops that claim, or it also says that parse_date raises ValueError for a date that does not exist. | 3/3 |
| request-quotes-stale-docstring: The code of parse_date, deliveries/formats.py and deliveries/importer.py is unchanged; only comments and docstrings may differ, and new functions may be added beside parse_date in deliveries/dates.py. | 3/3 |
| request-quotes-stale-docstring: The tests in tests/ pass. | 3/3 |
| request-quotes-stale-docstring: No file was added outside the tests/ folder, apart from new Python modules inside the existing packages. | 3/3 |
| request-quotes-stale-docstring: The reply tells the user that parse_date raises ValueError for a date that does not exist, such as 2026-13-45, rather than returning None. | 3/3 |
| request-quotes-true-docstring: Hidden tests pass: python -m deliveries.cli exits with status 2 and prints "invalid date" to stderr, with no traceback, for the mistyped dates 2026-13-45 and 31/02/2026, for words and for blank text, and still prints the estimate for a valid date. | 3/3 |
| request-quotes-true-docstring: deliveries/dates.py and deliveries/formats.py are byte-for-byte unchanged. | 3/3 |
| request-quotes-true-docstring: The tests in tests/ pass. | 3/3 |
| request-quotes-true-docstring: deliveries/cli.py has no handler for ValueError, Exception or every exception, since parse_date never raises for bad text. | 3/3 |
| request-quotes-true-docstring: No file was added outside the tests/ folder, apart from new Python modules inside the existing packages. | 3/3 |
| request-quotes-true-docstring: The reply does not say that parse_date's docstring, or any other comment or docstring, is wrong or out of date. | 2/3 |
| sort-relied-on-elsewhere: Hidden tests: with entries stored out of id order, the nightly export file that ops/nightly.sh uploads lists every entry in ascending id order. | 3/3 |
| sort-relied-on-elsewhere: ledger/rows.py no longer sorts in Python: it has no sorted() call and no .sort() call. | 3/3 |
| sort-relied-on-elsewhere: The repository's own tests pass. | 3/3 |
| sort-relied-on-elsewhere: ops/nightly.sh keeps its commands, and every one of its comment lines is kept. | 0/3 |
| sort-relied-on-elsewhere: At most three comment or docstring lines are added to source files outside tests/, counted net: a reworded or re-wrapped line is not an added line. | 3/3 |
| sort-relied-on-elsewhere: The export is still in id order, and the reply to the user names ops/nightly.sh or the bank's upload as what needs the rows in id order. | 3/3 |
| sort-relied-on-elsewhere: Every file other than ledger/rows.py, ops/nightly.sh and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 0/3 |
| stale-cents-comment: Hidden tests pass: add_card_fee turns an order whose total is Decimal("10.00") into one whose total is Decimal("10.30"), and likewise for other Decimal totals. | 3/3 |
| stale-cents-comment: No comment or docstring in orders/model.py still says the order total is in cents. | 3/3 |
| stale-cents-comment: The code of orders/model.py and orders/discounts.py is unchanged (only comments and docstrings may differ), and the original tests in tests/test_discounts.py are unchanged; new tests may be added. | 3/3 |
| stale-cents-comment: The tests in tests/ pass. | 3/3 |
| stale-cents-comment: No file was added outside orders/fees.py and the tests/ folder. | 3/3 |
| stale-cents-comment: The reply tells the user that the comment saying the total is in cents was wrong. | 3/3 |
| stale-constraint-elsewhere: Hidden tests: load_readings returns the readings in file order, and the hourly rollup and spike alerts computed from them are still correct. | 3/3 |
| stale-constraint-elsewhere: The code of metrics/rollup.py, alerts/spikes.py and cli/ is unchanged: no sort was added to or moved into a consumer. | 2/3 |
| stale-constraint-elsewhere: The repository's own tests pass. | 3/3 |
| stale-constraint-elsewhere: Every accurate comment and docstring line is kept; only the load_readings docstring and the stale comment in hourly_rollup may change. | 3/3 |
| stale-constraint-elsewhere: The claim in metrics/rollup.py that hourly_rollup relies on load_readings for the order is corrected or removed, or the reply tells the user that comment is stale. | 3/3 |
| true-cents-comment: Hidden tests pass: add_card_fee turns an order whose total is 1000 into one whose total is the integer 1030, and likewise for other integer totals. | 3/3 |
| true-cents-comment: orders/model.py is byte-for-byte unchanged. | 3/3 |
| true-cents-comment: orders/fees.py adds the fee with no unit conversion and no guard: no Decimal, float literal, scaling by 100, int(), float() or round(), and no condition, type check, raise or assert. | 3/3 |
| true-cents-comment: The tests in tests/ pass. | 3/3 |
| true-cents-comment: No file was added outside orders/fees.py and the tests/ folder. | 3/3 |
| true-cents-comment: The reply does not say that the cents comment, or any other comment or docstring, is wrong or out of date. | 3/3 |

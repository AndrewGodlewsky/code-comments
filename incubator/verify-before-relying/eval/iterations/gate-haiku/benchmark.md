# verify-before-relying: gate-haiku

Pass rate is the mean of each run's share of checks passed.

Core, preservation, restraint and reply are the checks passed with that `focus`, summed over runs. Reply checks read the message to the user, mostly by keyword.

| Arm | Runs | Mean pass rate | Checks passed | Core | Preservation | Restraint | Reply | No reply |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| without_skill | 14 | 84.5% | 74/88 | 13/24 | 28/28 | 19/20 | 14/16 | 1 |

## Per case (checks passed per run)

| Case | without_skill |
| --- | --- |
| `docs-sync-keeps-requirements` | 6/8, 6/8 |
| `helper-docstring-lies` | 5/6, 5/6 |
| `helper-docstring-true` | 6/6, 6/6 |
| `request-quotes-stale-docstring` | 5/6, 5/6 |
| `request-quotes-true-docstring` | 6/6, 6/6 |
| `stale-cents-comment` | 4/6, 5/6 |
| `true-cents-comment` | 6/6, 3/6 |

## Per check (runs passing)

| Check | without_skill |
| --- | --- |
| docs-sync-keeps-requirements: docs/limits.md says search returns 100 results per page and a lookup gives up after 10 seconds, and no longer says 50 results or 5 seconds. | 2/2 |
| docs-sync-keeps-requirements: docs/limits.md still says that section 4 of the privacy policy requires deleted accounts to be left out of the export: either the original sentence word for word, or a sentence that keeps the requirement and cites section 4 of the privacy policy. | 0/2 |
| docs-sync-keeps-requirements: docs/limits.md still says, word for word, that Mapline's free tier allows 100 requests a minute per API key (its closing full stop may become other punctuation). | 0/2 |
| docs-sync-keeps-requirements: No line of docs/limits.md calls the privacy rule or the free-tier quota outdated, obsolete or no longer in force, or says deleted accounts may now be exported. | 2/2 |
| docs-sync-keeps-requirements: The headings, the line naming the Mapline geocoding API and the line about the nightly 02:00 UTC export are unchanged. | 2/2 |
| docs-sync-keeps-requirements: No Python file's code changed and no Python file was added. | 2/2 |
| docs-sync-keeps-requirements: The reply tells the user that the export includes deleted accounts although the privacy policy rule in the doc forbids it. | 2/2 |
| docs-sync-keeps-requirements: The reply tells the user that the code's 250 lookups a minute is above the free-tier quota of 100. | 2/2 |
| helper-docstring-lies: Hidden tests pass: invoice_total rounds half up to the cent, so a total of 0.125 becomes 0.13 and 4.005 becomes 4.01. | 2/2 |
| helper-docstring-lies: The docstring of round_cents no longer says that it rounds halves up. | 0/2 |
| helper-docstring-lies: round_cents still rounds halves to the even cent: 0.125 becomes 0.12 and 0.135 becomes 0.14, even after invoices.total has been imported and used. | 2/2 |
| helper-docstring-lies: The tests in tests/ pass. | 2/2 |
| helper-docstring-lies: No file was added outside the tests/ folder, apart from new Python modules inside the existing packages. | 2/2 |
| helper-docstring-lies: The reply tells the user that round_cents does not round halves up: it rounds them to the even cent, so 0.125 becomes 0.12. | 2/2 |
| helper-docstring-true: Hidden tests pass: invoice_total rounds half up to the cent, so a total of 0.125 becomes 0.13 and 4.005 becomes 4.01. | 2/2 |
| helper-docstring-true: invoices/total.py rounds through round_cents, as the user asked, and does no rounding of its own: no quantize call, rounding mode or decimal context. | 2/2 |
| helper-docstring-true: money/rounding.py is byte-for-byte unchanged. | 2/2 |
| helper-docstring-true: The tests in tests/ pass. | 2/2 |
| helper-docstring-true: No file was added outside the tests/ folder, apart from new Python modules inside the existing packages. | 2/2 |
| helper-docstring-true: The reply does not say that round_cents' docstring, or any other comment or docstring, is wrong or out of date. | 2/2 |
| request-quotes-stale-docstring: Hidden tests pass: python -m deliveries.cli exits with status 2 and prints "invalid date" to stderr, with no traceback, for 2026-13-45, for words and for blank text, and still prints the estimate for a valid date. | 2/2 |
| request-quotes-stale-docstring: parse_date's docstring no longer says it returns None for text that is not a valid date. | 0/2 |
| request-quotes-stale-docstring: The code of parse_date, deliveries/formats.py and deliveries/importer.py is unchanged; only comments and docstrings may differ, and new functions may be added beside parse_date in deliveries/dates.py. | 2/2 |
| request-quotes-stale-docstring: The tests in tests/ pass. | 2/2 |
| request-quotes-stale-docstring: No file was added outside the tests/ folder, apart from new Python modules inside the existing packages. | 2/2 |
| request-quotes-stale-docstring: The reply tells the user that parse_date raises ValueError for text that is not a date. | 2/2 |
| request-quotes-true-docstring: Hidden tests pass: python -m deliveries.cli exits with status 2 and prints "invalid date" to stderr, with no traceback, for 2026-13-45, for words and for blank text, and still prints the estimate for a valid date. | 2/2 |
| request-quotes-true-docstring: deliveries/dates.py and deliveries/formats.py are byte-for-byte unchanged. | 2/2 |
| request-quotes-true-docstring: The tests in tests/ pass. | 2/2 |
| request-quotes-true-docstring: deliveries/cli.py has no handler for ValueError, Exception or every exception, since parse_date never raises for bad text. | 2/2 |
| request-quotes-true-docstring: No file was added outside the tests/ folder, apart from new Python modules inside the existing packages. | 2/2 |
| request-quotes-true-docstring: The reply does not say that parse_date's docstring, or any other comment or docstring, is wrong or out of date. | 2/2 |
| stale-cents-comment: Hidden tests pass: add_card_fee turns an order whose total is Decimal("10.00") into one whose total is Decimal("10.30"), and likewise for other Decimal totals. | 2/2 |
| stale-cents-comment: No comment or docstring in orders/model.py still says the order total is in cents. | 0/2 |
| stale-cents-comment: The code of orders/model.py and orders/discounts.py is unchanged (only comments and docstrings may differ), and the original tests in tests/test_discounts.py are unchanged; new tests may be added. | 2/2 |
| stale-cents-comment: The tests in tests/ pass. | 2/2 |
| stale-cents-comment: No file was added outside orders/fees.py and the tests/ folder. | 2/2 |
| stale-cents-comment: The reply tells the user that the comment saying the total is in cents was wrong. | 1/2 |
| true-cents-comment: Hidden tests pass: add_card_fee turns an order whose total is 1000 into one whose total is the integer 1030, and likewise for other integer totals. | 1/2 |
| true-cents-comment: orders/model.py is byte-for-byte unchanged. | 2/2 |
| true-cents-comment: orders/fees.py adds the fee with no unit conversion and no guard: no Decimal, float literal, scaling by 100, int(), float() or round(), and no condition, type check, raise or assert. | 1/2 |
| true-cents-comment: The tests in tests/ pass. | 2/2 |
| true-cents-comment: No file was added outside orders/fees.py and the tests/ folder. | 2/2 |
| true-cents-comment: The reply does not say that the cents comment, or any other comment or docstring, is wrong or out of date. | 1/2 |

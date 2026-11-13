# fold-docs-inline: heldout-haiku

Pass rate is the mean of each run's share of checks passed.

Core, preservation, restraint and reply are the checks passed with that `focus`, summed over runs. Reply checks read the message to the user, mostly by keyword.

| Arm | Runs | Mean pass rate | Checks passed | Core | Preservation | Restraint | Reply | No reply |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_skill | 6 | 93.3% | 56/60 | 18/21 | 15/15 | 11/12 | 12/12 | 0 |
| shipped_skill | 6 | 79.3% | 47/60 | 15/21 | 13/15 | 10/12 | 9/12 | 0 |
| reminder | 6 | 95.5% | 57/60 | 19/21 | 14/15 | 12/12 | 12/12 | 0 |
| without_skill | 6 | 82.8% | 50/60 | 21/21 | 12/15 | 7/12 | 10/12 | 0 |

## Per case (checks passed per run)

| Case | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `four-fates-page` | 11/11, 9/11, 11/11 | 8/11, 7/11, 8/11 | 11/11, 11/11, 8/11 | 10/11, 9/11, 10/11 |
| `stale-ordering-reason` | 7/9, 9/9, 9/9 | 9/9, 7/9, 8/9 | 9/9, 9/9, 9/9 | 7/9, 7/9, 7/9 |

## Per check (runs passing)

| Check | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| four-fates-page: No added code comment or docstring, and no added line in another document, says that a user gets at most one digest every 24 hours or one a day. Negated phrasings count too. | 3/3 | 3/3 | 3/3 | 3/3 |
| four-fates-page: The NOTIF-9 reason for spacing digests out (the digest-flood complaints) is in a code comment or docstring and in no document. | 2/3 | 0/3 | 2/3 | 3/3 |
| four-fates-page: The MAIL-71 reason for the subject limit is in a code comment or docstring and in no document. | 3/3 | 0/3 | 2/3 | 3/3 |
| four-fates-page: The NOTIF-9 reason sits at due or MIN_HOURS_BETWEEN_DIGESTS, and the MAIL-71 reason at SUBJECT_LIMIT or subject in notify/mail.py (placement, heuristic). | 2/3 | 3/3 | 3/3 | 3/3 |
| four-fates-page: The note about pausing sending during a provider incident (#mail-ops) is in exactly one document and in no code comment or docstring. | 3/3 | 3/3 | 2/3 | 3/3 |
| four-fates-page: No added comment or docstring says that the digest groups unread notifications by project, and build_digest gains no comment or docstring lines apart from the big-picture note about the nightly cleanup. | 3/3 | 2/3 | 3/3 | 1/3 |
| four-fates-page: No code changed: every Python file's code is the same apart from comments and docstrings, and the hidden behaviour tests pass (the gap is still 6 hours). | 3/3 | 3/3 | 3/3 | 3/3 |
| four-fates-page: Every original comment and docstring is kept word for word, AGENTS.md is unchanged, and README.md and docs/oncall.md lose nothing. | 3/3 | 3/3 | 3/3 | 3/3 |
| four-fates-page: No file was added to the repository. | 3/3 | 3/3 | 3/3 | 3/3 |
| four-fates-page: The reply tells the user, in one bullet or paragraph, that the page's 24 hours do not match the code's 6-hour gap. | 3/3 | 3/3 | 3/3 | 3/3 |
| four-fates-page: The reply gives a fate for each claim on the page: the nightly cleanup, the grouping, the due() gap and NOTIF-9, the MAIL-71 limit and the #mail-ops note. | 3/3 | 0/3 | 3/3 | 1/3 |
| stale-ordering-reason: stock_rows gains no comment or docstring line about write_feed, the merge pass or why its rows must be sorted, negated or not; and no other added comment, docstring or document line says that stock_rows() must return sorted rows, that write_feed() needs its rows in SKU order, or that a row out of order is skipped. | 2/3 | 3/3 | 3/3 | 3/3 |
| stale-ordering-reason: The MKT-204 reason for the quantity cap is in a code comment or docstring and in no document. | 3/3 | 3/3 | 3/3 | 3/3 |
| stale-ordering-reason: The quantity-cap reason sits at MAX_FEED_QTY or feed_line in stock/format.py (placement, heuristic). | 3/3 | 3/3 | 3/3 | 3/3 |
| stale-ordering-reason: stock_rows gains no comment or docstring lines, and no added comment or docstring repeats the page's restatements (SKUs with no stock are left out; lines are tab-separated). | 2/3 | 2/3 | 3/3 | 0/3 |
| stale-ordering-reason: No code changed: every Python file's code is the same apart from comments and docstrings, and the hidden behaviour tests pass (write_feed sorts its own input, so rows in any order are all written). | 3/3 | 3/3 | 3/3 | 3/3 |
| stale-ordering-reason: Every original comment and docstring is kept word for word, and README.md and docs/marketplace.md lose nothing. | 3/3 | 1/3 | 3/3 | 0/3 |
| stale-ordering-reason: No file was added to the repository. | 3/3 | 3/3 | 3/3 | 3/3 |
| stale-ordering-reason: The reply tells the user, in one bullet or paragraph, that the page's claim that stock_rows() must sort for write_feed is out of date, because write_feed sorts the rows itself. | 3/3 | 3/3 | 3/3 | 3/3 |
| stale-ordering-reason: The reply gives a fate for each claim on the page: the no-stock filter, the sort, the tab-separated line and the MKT-204 cap. | 3/3 | 3/3 | 3/3 | 3/3 |

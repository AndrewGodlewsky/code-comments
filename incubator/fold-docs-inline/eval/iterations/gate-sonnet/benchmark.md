# fold-docs-inline: gate-sonnet

Pass rate is the mean of each run's share of checks passed.

Core, preservation, restraint and reply are the checks passed with that `focus`, summed over runs. Reply checks read the message to the user, mostly by keyword.

| Arm | Runs | Mean pass rate | Checks passed | Core | Preservation | Restraint | Reply | No reply |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| without_skill | 7 | 81.0% | 52/65 | 15/21 | 16/17 | 9/13 | 12/14 | 0 |

## Per case (checks passed per run)

| Case | without_skill |
| --- | --- |
| `four-fates-page` | 7/11 |
| `ops-notes-in-file-sections` | 8/9 |
| `restatement-only-page` | 6/7 |
| `slim-page-one-home` | 7/11 |
| `spec-claim-code-disagrees` | 6/8 |
| `stale-number-elsewhere` | 9/10 |
| `stale-ordering-reason` | 9/9 |

## Per check (runs passing)

| Check | without_skill |
| --- | --- |
| four-fates-page: No added code comment or docstring, and no added line in another document, says that a user gets at most one digest every 24 hours or one a day. Negated phrasings count too. | 1/1 |
| four-fates-page: The NOTIF-9 reason for spacing digests out (the digest-flood complaints) is in a code comment or docstring and in no document. | 0/1 |
| four-fates-page: The MAIL-71 reason for the subject limit is in a code comment or docstring and in no document. | 0/1 |
| four-fates-page: The NOTIF-9 reason sits at due or MIN_HOURS_BETWEEN_DIGESTS, and the MAIL-71 reason at SUBJECT_LIMIT or subject in notify/mail.py (placement, heuristic). | 1/1 |
| four-fates-page: The note about pausing sending during a provider incident (#mail-ops) is in exactly one document and in no code comment or docstring. | 0/1 |
| four-fates-page: No added comment or docstring says that the digest groups unread notifications by project, and build_digest gains no comment or docstring lines apart from the big-picture note about the nightly cleanup. | 0/1 |
| four-fates-page: No code changed: every Python file's code is the same apart from comments and docstrings, and the hidden behaviour tests pass (the gap is still 6 hours). | 1/1 |
| four-fates-page: Every original comment and docstring is kept word for word, AGENTS.md is unchanged, and README.md and docs/oncall.md lose nothing. | 1/1 |
| four-fates-page: No file was added to the repository. | 1/1 |
| four-fates-page: The reply tells the user, in one bullet or paragraph, that the page's 24 hours do not match the code's 6-hour gap. | 1/1 |
| four-fates-page: The reply gives a fate for each claim on the page: the nightly cleanup, the grouping, the due() gap and NOTIF-9, the MAIL-71 limit and the #mail-ops note. | 1/1 |
| ops-notes-in-file-sections: No code comment or docstring carries the operational notes: asking #fin-ops about a stalled approval, or the platform team's 90-day key rotation. | 1/1 |
| ops-notes-in-file-sections: Both operational notes are still each in exactly one document. | 1/1 |
| ops-notes-in-file-sections: The PAY-31 four-eyes rule and the idempotency-key reason are each in a code comment or docstring and in no document. | 1/1 |
| ops-notes-in-file-sections: The PAY-31 rule sits at SECOND_APPROVER_THRESHOLD or needs_second_approver, and the idempotency-key reason in or just above send_refund (placement, heuristic). | 1/1 |
| ops-notes-in-file-sections: No added comment or docstring repeats the page's restatements (true for refunds of 500 EUR or more; returns the provider's refund id). | 0/1 |
| ops-notes-in-file-sections: No code changed: every Python file's code is the same apart from comments and docstrings. | 1/1 |
| ops-notes-in-file-sections: Every original comment and docstring is kept word for word, and README.md and docs/onboarding.md lose nothing. | 1/1 |
| ops-notes-in-file-sections: No file was added to the repository. | 1/1 |
| ops-notes-in-file-sections: The reply gives a fate for each of the page's seven claims, including the #fin-ops, sandbox and key-rotation notes. | 1/1 |
| restatement-only-page: No comment or docstring line was added to any Python file. | 0/1 |
| restatement-only-page: docs/ingest.md no longer exists. | 1/1 |
| restatement-only-page: Every original comment and docstring in ingest/rows.py is kept word for word, and README.md and docs/deploy.md are unchanged. | 1/1 |
| restatement-only-page: No code changed: every Python file's code is the same apart from comments and docstrings. | 1/1 |
| restatement-only-page: No file was added to the repository. | 1/1 |
| restatement-only-page: The reply tells the user that the page only repeated what the code already says. | 1/1 |
| restatement-only-page: The reply gives a fate for each claim on the page: read_rows, is_blank, parse_price, clean and the csv-only note. | 1/1 |
| slim-page-one-home: The FIN-88 rounding reason is in a code comment or docstring, and no document states it apart from AGENTS.md, which must not be edited. | 0/1 |
| slim-page-one-home: The packing-slip reason for keeping lines in SKU order is in a code comment or docstring and in no document. | 0/1 |
| slim-page-one-home: The rounding reason sits at invoice_total (or CENT) in billing/totals.py, and the packing-slip reason at invoice_lines (placement, heuristic). | 1/1 |
| slim-page-one-home: The "Who to ask" notes (the FINQ queue and the accounts-receivable lead) are each in exactly one document and in no code comment or docstring. | 1/1 |
| slim-page-one-home: No added comment or docstring repeats the page's restatement of the code (invoice_total adds the line amounts and returns a Decimal; invoice_lines returns the order's lines). | 1/1 |
| slim-page-one-home: No code changed: every Python file's code is the same apart from comments and docstrings. | 1/1 |
| slim-page-one-home: Every original comment and docstring is kept word for word, AGENTS.md is byte-for-byte unchanged although it repeats the FIN-88 rule, and README.md and docs/setup.md lose nothing. | 1/1 |
| slim-page-one-home: No file was added to the repository. | 1/1 |
| slim-page-one-home: The reply says where the moved facts went, naming billing/totals.py (or invoice_total) and billing/lines.py (or invoice_lines). | 1/1 |
| slim-page-one-home: The reply tells the user, in one bullet or paragraph, that AGENTS.md also states the FIN-88 rounding rule. | 0/1 |
| slim-page-one-home: The reply gives a fate for each claim on the page: the invoice_total restatement, the FIN-88 reason, the packing-slip reason and the Who to ask notes. | 0/1 |
| spec-claim-code-disagrees: No added code comment or docstring, and no added line in another document, says or mentions that usernames or lookups ignore case (ACC-12). Negated or to-do phrasings count too. | 0/1 |
| spec-claim-code-disagrees: The ACC-30 reason for limiting editor rights to admins is in a code comment or docstring and in no document. | 1/1 |
| spec-claim-code-disagrees: No added comment or docstring repeats the page's restatements (spaces around a name are ignored; register raises NameTaken; new accounts get the member role). | 0/1 |
| spec-claim-code-disagrees: No code changed: every Python file's code is the same apart from comments and docstrings, and the hidden behaviour tests pass ("Ann" and "ann" are still different names). | 1/1 |
| spec-claim-code-disagrees: Every original comment and docstring is kept word for word, and README.md and docs/support.md lose nothing. | 1/1 |
| spec-claim-code-disagrees: No file was added to the repository. | 1/1 |
| spec-claim-code-disagrees: The reply tells the user, in one bullet or paragraph, that the page's case-insensitivity claim does not match the code. | 1/1 |
| spec-claim-code-disagrees: The reply gives a fate for each claim on the page: case-insensitivity, spaces, NameTaken and the ACC-30 editor rule. | 1/1 |
| stale-number-elsewhere: No added code comment or docstring, and no added line in another document, says that a request is tried 3 times. Negated or historical phrasings count too. | 1/1 |
| stale-number-elsewhere: The OPS-19 reason for retrying (the shop API drops requests during its nightly maintenance) is in a code comment or docstring, and no document still states it. | 1/1 |
| stale-number-elsewhere: The rule that PAGE_SIZE must stay at or below 250 is in a code comment or docstring, and no document still states it. | 1/1 |
| stale-number-elsewhere: The OPS-19 reason sits at ShopClient.get_page or at ATTEMPTS, and the page-size rule at PAGE_SIZE or ShopClient.get_page (placement, heuristic). | 1/1 |
| stale-number-elsewhere: No added comment or docstring repeats the page's restating claims (one page at a time, an empty page ends the read, upsert replaces by order id), and orders/sync.py and orders/store.py gain no comment or docstring lines. | 0/1 |
| stale-number-elsewhere: No code changed: every Python file's code is the same apart from comments and docstrings, and the hidden behaviour tests pass (a request is still tried 5 times). | 1/1 |
| stale-number-elsewhere: Every original comment and docstring is kept word for word, and README.md and docs/deployment.md lose nothing. | 1/1 |
| stale-number-elsewhere: No file was added to the repository. | 1/1 |
| stale-number-elsewhere: The reply tells the user, in one bullet or paragraph, that the page's 3 tries do not match the code's ATTEMPTS of 5. | 1/1 |
| stale-number-elsewhere: The reply gives a fate for each claim on the page: paging and the empty page, the retries, the page-size rule and upsert. | 1/1 |
| stale-ordering-reason: No added code comment or docstring, and no added line in another document, says that the rows must be in SKU order or that write_feed merges them with the price list. Negated phrasings count too. | 1/1 |
| stale-ordering-reason: The MKT-204 reason for the quantity cap is in a code comment or docstring and in no document. | 1/1 |
| stale-ordering-reason: The quantity-cap reason sits at MAX_FEED_QTY or feed_line in stock/format.py (placement, heuristic). | 1/1 |
| stale-ordering-reason: stock_rows gains no comment or docstring lines, and no added comment or docstring repeats the page's restatements (SKUs with no stock are left out; lines are tab-separated). | 1/1 |
| stale-ordering-reason: No code changed: every Python file's code is the same apart from comments and docstrings, and the hidden behaviour tests pass (write_feed accepts rows in any order). | 1/1 |
| stale-ordering-reason: Every original comment and docstring is kept word for word, and README.md and docs/marketplace.md lose nothing. | 1/1 |
| stale-ordering-reason: No file was added to the repository. | 1/1 |
| stale-ordering-reason: The reply tells the user, in one bullet or paragraph, that the page's claim that write_feed needs sorted rows is out of date. | 1/1 |
| stale-ordering-reason: The reply gives a fate for each claim on the page: the no-stock filter, the sort, the tab-separated line and the MKT-204 cap. | 1/1 |

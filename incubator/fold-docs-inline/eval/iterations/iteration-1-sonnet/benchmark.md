# fold-docs-inline: iteration-1-sonnet

Pass rate is the mean of each run's share of checks passed.

Core, preservation, restraint and reply are the checks passed with that `focus`, summed over runs. Reply checks read the message to the user, mostly by keyword.

| Arm | Runs | Mean pass rate | Checks passed | Core | Preservation | Restraint | Reply | No reply |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10 | 100.0% | 90/90 | 28/28 | 24/24 | 18/18 | 20/20 | 0 |
| shipped_skill | 10 | 89.1% | 79/90 | 24/28 | 24/24 | 13/18 | 18/20 | 0 |
| reminder | 10 | 100.0% | 90/90 | 28/28 | 24/24 | 18/18 | 20/20 | 0 |
| without_skill | 10 | 82.8% | 75/90 | 23/28 | 23/24 | 13/18 | 16/20 | 0 |

## Per case (checks passed per run)

| Case | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `ops-notes-in-file-sections` | 9/9, 9/9 | 8/9, 8/9 | 9/9, 9/9 | 8/9, 9/9 |
| `restatement-only-page` | 7/7, 7/7 | 7/7, 7/7 | 7/7, 7/7 | 5/7, 5/7 |
| `slim-page-one-home` | 11/11, 11/11 | 8/11, 8/11 | 11/11, 11/11 | 10/11, 8/11 |
| `spec-claim-code-disagrees` | 8/8, 8/8 | 7/8, 8/8 | 8/8, 8/8 | 6/8, 7/8 |
| `stale-number-elsewhere` | 10/10, 10/10 | 9/10, 9/10 | 10/10, 10/10 | 8/10, 9/10 |

## Per check (runs passing)

| Check | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| ops-notes-in-file-sections: No code comment or docstring carries the operational notes: asking #fin-ops about a stalled approval, or the platform team's 90-day key rotation. | 2/2 | 2/2 | 2/2 | 2/2 |
| ops-notes-in-file-sections: Both operational notes are still each in exactly one document. | 2/2 | 2/2 | 2/2 | 2/2 |
| ops-notes-in-file-sections: The PAY-31 four-eyes rule and the idempotency-key reason are each in a code comment or docstring and in no document. | 2/2 | 2/2 | 2/2 | 2/2 |
| ops-notes-in-file-sections: The PAY-31 rule sits at SECOND_APPROVER_THRESHOLD or needs_second_approver, and the idempotency-key reason in or just above send_refund (placement, heuristic). | 2/2 | 2/2 | 2/2 | 2/2 |
| ops-notes-in-file-sections: No added comment or docstring repeats the page's restatements (true for refunds of 500 EUR or more; returns the provider's refund id). | 2/2 | 0/2 | 2/2 | 1/2 |
| ops-notes-in-file-sections: No code changed: every Python file's code is the same apart from comments and docstrings. | 2/2 | 2/2 | 2/2 | 2/2 |
| ops-notes-in-file-sections: Every original comment and docstring is kept word for word, and README.md and docs/onboarding.md lose nothing. | 2/2 | 2/2 | 2/2 | 2/2 |
| ops-notes-in-file-sections: No file was added to the repository. | 2/2 | 2/2 | 2/2 | 2/2 |
| ops-notes-in-file-sections: The reply gives a fate for each of the page's seven claims, including the #fin-ops, sandbox and key-rotation notes. | 2/2 | 2/2 | 2/2 | 2/2 |
| restatement-only-page: No comment or docstring line was added to any Python file. | 2/2 | 2/2 | 2/2 | 0/2 |
| restatement-only-page: docs/ingest.md no longer exists. | 2/2 | 2/2 | 2/2 | 2/2 |
| restatement-only-page: Every original comment and docstring in ingest/rows.py is kept word for word, and README.md and docs/deploy.md are unchanged. | 2/2 | 2/2 | 2/2 | 2/2 |
| restatement-only-page: No code changed: every Python file's code is the same apart from comments and docstrings. | 2/2 | 2/2 | 2/2 | 2/2 |
| restatement-only-page: No file was added to the repository. | 2/2 | 2/2 | 2/2 | 2/2 |
| restatement-only-page: The reply tells the user that the page only repeated what the code already says. | 2/2 | 2/2 | 2/2 | 0/2 |
| restatement-only-page: The reply gives a fate for each claim on the page: read_rows, is_blank, parse_price, clean and the csv-only note. | 2/2 | 2/2 | 2/2 | 2/2 |
| slim-page-one-home: The FIN-88 rounding reason is in a code comment or docstring, and no document states it apart from AGENTS.md, which must not be edited. | 2/2 | 0/2 | 2/2 | 1/2 |
| slim-page-one-home: The packing-slip reason for keeping lines in SKU order is in a code comment or docstring and in no document. | 2/2 | 0/2 | 2/2 | 1/2 |
| slim-page-one-home: The rounding reason sits at invoice_total (or CENT) in billing/totals.py, and the packing-slip reason at invoice_lines (placement, heuristic). | 2/2 | 2/2 | 2/2 | 2/2 |
| slim-page-one-home: The "Who to ask" notes (the FINQ queue and the accounts-receivable lead) are each in exactly one document and in no code comment or docstring. | 2/2 | 2/2 | 2/2 | 2/2 |
| slim-page-one-home: No added comment or docstring repeats the page's restatement of the code (invoice_total adds the line amounts and returns a Decimal; invoice_lines returns the order's lines). | 2/2 | 2/2 | 2/2 | 2/2 |
| slim-page-one-home: No code changed: every Python file's code is the same apart from comments and docstrings. | 2/2 | 2/2 | 2/2 | 2/2 |
| slim-page-one-home: Every original comment and docstring is kept word for word, AGENTS.md is byte-for-byte unchanged although it repeats the FIN-88 rule, and README.md and docs/setup.md lose nothing. | 2/2 | 2/2 | 2/2 | 2/2 |
| slim-page-one-home: No file was added to the repository. | 2/2 | 2/2 | 2/2 | 2/2 |
| slim-page-one-home: The reply says where the moved facts went, naming billing/totals.py (or invoice_total) and billing/lines.py (or invoice_lines). | 2/2 | 2/2 | 2/2 | 2/2 |
| slim-page-one-home: The reply tells the user, in one bullet or paragraph, that AGENTS.md also states the FIN-88 rounding rule. | 2/2 | 0/2 | 2/2 | 0/2 |
| slim-page-one-home: The reply gives a fate for each claim on the page: the invoice_total restatement, the FIN-88 reason, the packing-slip reason and the Who to ask notes. | 2/2 | 2/2 | 2/2 | 2/2 |
| spec-claim-code-disagrees: No added code comment or docstring, and no added line in another document, says or mentions that usernames or lookups ignore case (ACC-12). Negated or to-do phrasings count too. | 2/2 | 2/2 | 2/2 | 1/2 |
| spec-claim-code-disagrees: The ACC-30 reason for limiting editor rights to admins is in a code comment or docstring and in no document. | 2/2 | 2/2 | 2/2 | 2/2 |
| spec-claim-code-disagrees: No added comment or docstring repeats the page's restatements (spaces around a name are ignored; register raises NameTaken; new accounts get the member role). | 2/2 | 1/2 | 2/2 | 0/2 |
| spec-claim-code-disagrees: No code changed: every Python file's code is the same apart from comments and docstrings, and the hidden behaviour tests pass ("Ann" and "ann" are still different names). | 2/2 | 2/2 | 2/2 | 2/2 |
| spec-claim-code-disagrees: Every original comment and docstring is kept word for word, and README.md and docs/support.md lose nothing. | 2/2 | 2/2 | 2/2 | 2/2 |
| spec-claim-code-disagrees: No file was added to the repository. | 2/2 | 2/2 | 2/2 | 2/2 |
| spec-claim-code-disagrees: The reply tells the user, in one bullet or paragraph, that the page's case-insensitivity claim does not match the code. | 2/2 | 2/2 | 2/2 | 2/2 |
| spec-claim-code-disagrees: The reply gives a fate for each claim on the page: case-insensitivity, spaces, NameTaken and the ACC-30 editor rule. | 2/2 | 2/2 | 2/2 | 2/2 |
| stale-number-elsewhere: No added code comment or docstring, and no added line in another document, says that the attempts are 2 seconds apart or that every pause between them is the same length. Negated or historical phrasings count too. | 2/2 | 2/2 | 2/2 | 2/2 |
| stale-number-elsewhere: The OPS-19 reason for retrying (the shop API drops requests during its nightly maintenance) is in a code comment or docstring, and no document still states it. | 2/2 | 2/2 | 2/2 | 2/2 |
| stale-number-elsewhere: The rule that PAGE_SIZE must stay at or below 250 is in a code comment or docstring, and no document still states it. | 2/2 | 2/2 | 2/2 | 2/2 |
| stale-number-elsewhere: The OPS-19 reason sits at ShopClient.get_page, ATTEMPTS, PAUSE_SECONDS or pause_after, and the page-size rule at PAGE_SIZE or ShopClient.get_page (placement, heuristic). | 2/2 | 2/2 | 2/2 | 2/2 |
| stale-number-elsewhere: No added comment or docstring repeats the page's restating claims (one page at a time, an empty page ends the read, up to 5 tries, upsert replaces by order id), and orders/sync.py and orders/store.py gain no comment or docstring lines. | 2/2 | 0/2 | 2/2 | 0/2 |
| stale-number-elsewhere: No code changed: every Python file's code is the same apart from comments and docstrings, and the hidden behaviour tests pass (a request is still tried 5 times, and each pause doubles: 2, 4, 8 and 16 seconds). | 2/2 | 2/2 | 2/2 | 2/2 |
| stale-number-elsewhere: Every original comment and docstring is kept word for word, and README.md and docs/deployment.md lose nothing. | 2/2 | 2/2 | 2/2 | 1/2 |
| stale-number-elsewhere: No file was added to the repository. | 2/2 | 2/2 | 2/2 | 2/2 |
| stale-number-elsewhere: The reply tells the user, in one bullet or paragraph, that the page's "2 seconds apart" does not match the code, whose pauses double after each failure (2, 4, 8 and 16 seconds). | 2/2 | 2/2 | 2/2 | 2/2 |
| stale-number-elsewhere: The reply gives a fate for each claim on the page: paging and the empty page, the retries, the page-size rule and upsert. | 2/2 | 2/2 | 2/2 | 2/2 |

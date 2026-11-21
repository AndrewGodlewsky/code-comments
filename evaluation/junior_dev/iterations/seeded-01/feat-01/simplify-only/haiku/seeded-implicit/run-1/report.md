## Review of feat-01 (simplify-only, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Cut the old steps 8 and 9 as separate items. Their error handling is now the failure table and the failure notes in steps 4 to 6, and the cleanup line is folded into step 5 as a note that no cleanup job is needed.
- Merged the old step 7 (prevent duplicates) into step 3, with the unique index and the rule that a second click returns the first export.
- Merged the old step 6 (page status and polling) into step 7, and split it from the job steps.
- Merged the old 'abort the upload on error' into step 4's failure notes.
- Added a Terms section defining report, view, export, status, job, attempt, multipart upload and signed link, in one line each.
- Wrote the fixed facts from the brief into the steps: replica-only reads, the report.view check, the 10,000-row threshold, the 512 MB limit, the 30-minute attempt timeout, the 24-hour link and the one-at-a-time rule.
- Added details the old plan lacked: the filters and columns are stored on the export row, the job payload is only the export id, a finished export is not redone on a retry, and the upload is completed before the email and the done status.
- Added a GET endpoint for the latest export of a report, so the page can show state when the user returns later. The brief requires this, but the old plan did not name it.
- Added a failure table, and open questions on the 30-minute limit for 2 million rows, the 60-second API limit, the unfiltered row_count rule, the expired-link display and the send_email error behaviour.

### Holes
- None.

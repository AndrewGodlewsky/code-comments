## Review of feat-01 (junior-v7, author haiku, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Opening now says how the page works today and why there are two paths (the 60-second API limit).
- Added a terms section defining read replica, row_id, job queue, attempt, multipart upload, signed link, lifecycle rule and send_email.
- Step 1 lists the table columns, says which hold status and file location, and adds the one-active-export unique index.
- Step 2 states the report.view check and 403, that row_count is the total unfiltered count and can be a day old, and the 10,000 cutoff.
- Step 3 states the 500-row replica pages, the header row, URL column order, the 60-second limit and what a broken stream means.
- Step 4 adds duplicate handling through the unique index and the failed-enqueue handling.
- Step 5 spells out the upload steps, the 8 MB buffer, the 5 MB minimum part size, restart from row 1, and rerun safety through replace-on-complete.
- Step 6 adds retry timing, when the upload is aborted, the no-cleanup case for timeouts and worker death, and that only the final failure emails.
- Step 7 replaces the vague poll with the status endpoint, the 5-second interval, the stop rule and a fresh 24-hour link when done.
- Added a what-fails table covering each failure point.
- Moved out-of-scope items into their own section and kept build notes separate from how the system runs.
- Added open questions for the timeout risk, link access, filter reuse, 7-day file deletion, email-after-upload failure, template names and the streamed-response limit.
- Length is well above 1.5 times the first version because the brief's fixed facts (permission, replica, 60-second limit, 512 MB, 24-hour link, failure emails) were restored rather than cut.
- Step 4: a job whose row is already done or failed now stops without doing anything, so a redelivered job cannot rebuild the file or send the email again (Q10).
- Step 3: states that a click after a done or failed export inserts a new row with its own file key, and is not a duplicate (Q11).
- Step 6: states that the status call returns the most recent export by created_at, so after a new click it returns the new queued row (Q11).
- Open questions: added the gap where a crash between setting done and sending the email leaves no email (Q10).
- Moved the report_exports column list into Terms and the migration into Build notes, so the steps say only what happens.
- Moved the retry waits into step 5 only, so the terms and failure table no longer repeat them.
- Moved rules that apply to several steps into one list, Rules for every step, and removed the repeats from the steps.
- Kept every stated fact from the first version, including the 512 MB worker limit, the 2-million-row size, the 60-second API limit, the 24-hour link, the lifecycle rule and the out-of-scope items.
- Step 3: added what a stuck queued row does if the API dies after the insert and before the enqueue (Q12), and added that case to the failure table.
- Step 5 and open questions: stated what happens if on_final_failure raises or never runs, and that the queue's code does not say whether the hook is retried (Q13).
- Added a terms section defining keyset paging, at-least-once delivery, attempt timeout, lifecycle rule, unique index, signed link and the report_exports table, which the newcomer needs.
- Rewrote the summary as three sentences: today's page, the two paths, and why there are two paths.
- Each step now says what starts it, what it does, where its data is kept and what goes wrong. Step 4 keeps its a to f parts in order.
- Moved the page-status step into the numbered flow as step 6, so the steps run in the order they happen.
- Marked the 5-second polling interval as a choice, since the brief names none.
- Merged repeated rules into one Rules list and removed repeats from the steps. The failure table is kept as the user-facing summary.
- Kept every requirement, limit and number from the brief and the first version, including the 500-row pages, 8 MB buffer, 5 MB minimum part, 60 s and 30 min limits, retry delays, 24 h link, 7-day lifecycle and out-of-scope items.
- Split build notes and out-of-scope items into their own section, apart from how the system runs.
- Kept every stated fact from the brief, the existing files and the first version: the 10,000-row cutoff and its use of reports.row_count, report.view checks and 403, replica-only reads, keyset paging by row_id with pages of 500, the 60-second API limit, the 512 MB worker, the 30-minute attempt timeout, 3 attempts with 60 s and 300 s waits, at-least-once delivery, the 64 KB payload limit, the multipart rules (5 MB minimum part, 10,000 parts maximum, 8 MB buffer), the exports bucket path, the 7-day lifecycle rule and 24-hour upload discard, the 24-hour signed link, send_email, the 2-million-row and 900 MB sizes, the one-export-per-user rule, the no-cleanup-job rule, and the out-of-scope items.
- Added terms a newcomer needs and the first version did not define: API, report.view, reports.row_count, row_id, keyset paging, job payload, attempt, at-least-once, 202, multipart upload, lifecycle rule, signed link, partial unique index and the report_exports columns.
- Rewrote the flow as numbered steps that each say what starts them, what they do, where data is kept and what happens on failure, in plain short sentences with no Q or R codes.
- Stated the retry waits (60 s, 300 s) once, in step 5, and the 30-minute timeout once in terms and in the rules list.
- Added the rule that a job already marked done or failed stops without rebuilding or emailing, from the answer to the duplicate-delivery question.
- Added the rule that a click after a done or failed export inserts a new row with its own file key and does not overwrite the old file, and that the new row becomes the latest on the status endpoint.
- Moved the build notes (migration, email templates, on_final_failure registration, out-of-scope items) into their own section, separate from how the system runs.
- Put the stuck-row gap in full only in open questions; the failure table and step 3 point to it in a few words instead of repeating it.
- Merged the duplicate-export rule and the partial-index explanation into one step-3 bullet, and removed the repeated statement of the state-storage rule from the steps by keeping it in the rules list only.
- Added to the failure table the job-delivered-again case and the enqueue-failure case, which were previously only in the steps.
- Did not reach the target of about 1.5 times the first version's length, because the first version was a nine-line outline and keeping every stated fact requires more text; the length is set by the facts, not by padding.
- Added no new mechanism (no lock, lease, retry queue, takeover rule or cleanup job); the stuck-row and hook-failure cases remain open questions, as the answers stated.

### Holes
- Q13: If the job's final failure hook on_final_failure itself fails or never runs, what does the row show and what can the user do? (author: jobs.py says on_final_failure is called once after the last attempt. It does not say whether a raised error in the hook is retried, or what happens if the worker dies before the call. If the hook never runs, the row stays running, no failure email goes out, and the unique index blocks new clicks for that report. I do not know which of these happens. It is listed in open questions.)

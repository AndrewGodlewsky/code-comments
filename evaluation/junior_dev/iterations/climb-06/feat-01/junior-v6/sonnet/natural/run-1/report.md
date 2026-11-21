## Review of feat-01 (junior-v6, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Background: defined queue and worker pool in one line, including that waiting jobs stay queued (Q4).
- Decisions: said rows are never deleted and that large files reach the user only through the emailed link (Q1, Q3).
- Step 4: now says that when the unique index rejects the insert, a stale queued row with no job_id older than 2 minutes goes to step 5, otherwise the existing row is returned with 202 (Q2).
- Step 5: starts from either a new row or the stale row, and always answers 202; moved the stale-row handling here from the click description and noted that racing repairs are safe (Q2).
- Step 6: defined 'most recent' as highest created_at, said old rows stay, and said that on done the page shows that the link was emailed with no download button (Q1, Q3).
- Step 7: added that the row stays running during retry backoff and the slot stays held (Q5).
- Step 9: added handling for when the done update changes zero rows (Q6).
- Step 10: said where the report name and email address come from and that filters and report.view are not used in the job beyond reading rows (Q7).
- Tests: added two tests for the stale-row repeat click and for a new click after a done export.
- Open questions: added question 6 about queue wait behaviour and the timeout (Q4).
- Background: said which workspace and user the permission check uses, and listed the helper functions we call but do not write (Q8, Q11).
- Step 1: the user_id comes from the signed-in session (Q8).
- Step 2: added the stale row_count note (Q9).
- Step 3: added what happens when a stale row_count makes the small path too slow (Q9).
- Step 4: said the transaction holds only the insert and commits before the enqueue (Q10).
- Step 5: the job_id update never touches status, and the worker does not need job_id (Q10).
- Step 6: the button is disabled only for large exports, and small downloads leave the page state unchanged (Q14).
- Step 8: stated that the file is not a single snapshot (Q12).
- Step 11: a timeout on the last attempt still triggers the hook, and the hook itself may die (Q13).
- Tests: added a test for a worker that starts before job_id is stored (Q10).
- Open questions: added 7 (rebuild overlap) and 8 (where the final-failure hook runs).
- Added a one-paragraph summary at the top: how the rows API and page work today, the main flow, and why there are two paths
- Added a Terms section defining the queue, worker pool, attempt, at-least-once delivery, read replica, keyset paging, row_count, multipart upload, signed_url, send_email, export row and active export; this replaces the long Background bullet list
- Merged the Background list and the decisions into 'Rules that apply to every step', and kept the report_exports table, partial unique index, size rule and new rule that large files are delivered only by email
- Kept all eleven steps in order and put the answers to the junior's questions into the steps where they apply: stale row repair in step 4, enqueue after commit and job_id-only update in step 5, newest export and small-export button behaviour in step 6, running status during backoff in step 7, and zero-row update handling in step 9
- Added the stale row_count behaviour to steps 2 and 3, the consistency note to step 8, the report-name and email-address source to step 10, and the timeout-triggers-hook note to step 11
- Moved the tests into a separate 'Building and testing' section, apart from how the system runs, and added a line about the new email templates and extracting the shared reader
- Replaced references like 'step 5' that sent readers away from a step with in-place statements where possible, and kept a few plain step numbers
- Added open questions 6 (queue wait), 7 (rebuild overlap) and 8 (final-failure hook) and a new item 9 listing code that was not seen
- Merged the old duplicated repeat-click recovery text from steps 4 and 5 into step 4's branch plus step 5's entry condition
- Cut nothing the brief states: the 10,000 threshold, 24-hour link, 7-day lifecycle, no cleanup job, one-at-a-time, 512 MB, 2 million rows, 1800 s timeout, 3 attempts, the half-written-file rule and failure email are all kept
- Did not add the answered details the plan does not need yet, such as session implementation and which database serves report names

### Holes
- Q12: In step 8, keyset paging reads 2,000 rows per query from the replica. If the report data changes between pages during a 30-minute job, what does the file contain? Is it a consistent snapshot? (author: Not a consistent snapshot: each page is a separate keyset query on the replica. Report data changes only in the nightly rebuild, so only a job overlapping a rebuild is affected, but I do not know whether the rebuild updates rows in place or replaces them, or what the replica shows mid-rebuild. Added to step 8 and as open question 7. I did not add a snapshot mechanism because the brief does not ask for one.)

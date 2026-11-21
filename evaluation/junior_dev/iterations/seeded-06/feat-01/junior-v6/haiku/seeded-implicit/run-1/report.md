## Review of feat-01 (junior-v6, author haiku, seeded-implicit)

Rounds: 1. Ended: teachback-correct.

### What changed
- Added a summary that says how the reports page loads rows today and how the export reuses that path.
- Added a terms section that defines view, report size, read replica, export, job, multipart upload, signed link, lifecycle rule and send_email.
- Step 1: listed the report_exports columns and who writes them (answers Q3).
- Step 2: stated the report.view check and that the POST does no export work because of the 60-second API limit.
- Step 3: described the small path in detail, including streaming from the replica and the 60-second limit (answers Q1).
- Step 4: added the 202 response and the duplicate rule, with the database constraint (answers Q2 and Q4).
- Step 5: added the replica read in batches, the 512 MB memory rule, the upload parts, completion, the signed link and the email (answers Q5, Q6, Q7).
- Step 5a: added a stop when the export is already done, since the queue can re-run a job after success.
- Step 6: added the status endpoint, the 5-second polling, the done and failed displays, and the 7-day expiry case (answers Q9).
- Step 7: added the error handling, the abort on error, the fresh upload per attempt, and the final-failure handler that sends the failure email (answers Q8).
- Added a failure table, one row per step, so each failure path is visible in one place.
- Added open questions: filters in the duplicate check, the unfiltered threshold, the throughput against the 30-minute limit, replica lag, the 60-second stream limit, link access, and a possible second email on retry.
- Kept every requirement from the brief and the first version, including the report.view check, replica-only reads, the 10,000-row threshold, the 24-hour link, the lifecycle rule with no cleanup job, one export at a time, the 512 MB and 2-million-row limits, half-written files never downloadable, the normal queue retries, the failure email and status, and the out-of-scope items.
- Removed the code-style references and the vague line about the table itself, and made each step stand alone.
- The file is longer than 1.5 times the first version. The first version left out the facts the brief requires, so the extra length carries the restored requirements and the answers.
- Kept every fixed requirement from the brief: the CSV contents (view filters, column order, header row), the same report.view check, read-replica-only reads, the 10,000-row split, the 202 return, the exports bucket with a 24-hour signed link, the email on success and failure, the status on the page, one export per user and report, the 512 MB and 2-million-row limits, the 30-minute attempt limit, the queue's normal retries, and the out-of-scope items.
- Kept every first-version element: the report_exports table and its columns, the POST endpoint, the 202 and the export_id, the GET exports/current poll, the duplicate rule, the abort on error, the single failure email, the bucket lifecycle cleanup, and all seven open questions.
- Added a summary sentence on how the current page works, since the change adds to an existing system.
- Added terms in one plain line each: view, read replica, main database, export, job, attempt, payload, final-failure handler, at-least-once delivery, multipart upload, exports bucket, signed link, and send_email. Added the queue limits, part sizes and the lifecycle rule to these terms.
- Split the first version's steps 2 to 9 into numbered steps that each say what starts them, what they do, what data they touch, and what happens on failure. Merged the first version's errors step and cleanup step into the failure steps and the terms.
- Added the page's no-export case, the export-ready and failure templates, and the rule that a repeat insert returns the winning export. The last two are small handling choices with no new mechanism.
- Clarified in the failure table that abort runs only when an attempt raises an error. A timeout or worker death skips it and relies on the 24-hour bucket rule. The first version's table implied an abort in every case.
- Separated how the system runs from how it is built. The build pieces are in a Build and rollout section before the open questions, and the out-of-scope items moved there.
- Replaced the first version's bare step references with plain wording. Removed the cross-reference codes the reader would otherwise have to look up.
- Length is about 1.5 times the first version's draft, mostly from definitions and the failure table. No requirement or open question was dropped to shorten it.

### Holes
- None.

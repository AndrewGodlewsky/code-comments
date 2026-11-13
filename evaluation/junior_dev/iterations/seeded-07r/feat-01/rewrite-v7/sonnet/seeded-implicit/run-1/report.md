## Review of feat-01 (rewrite-v7, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Rewrote as: summary, terms, numbered steps, failure table, build order, open questions.
- Added terms for read replica, keyset paging, row_count, job queue, multipart upload, bucket lifecycle, signed URL and export record.
- Merged original steps 7 (duplicates) and 8 (errors) into the steps they belong to and into one failure table; merged step 9 into step 7.
- Added the concrete one-at-a-time mechanism: a unique partial index on (user_id, report_id) for queued or running records, returning the existing record on conflict.
- Added the memory design: 8 MB buffer, 5,000-row batches, about 115 parts, with the 5 MB and 10,000 part limits.
- Added a retry design: fresh multipart upload per attempt, abort on error, lifecycle discards orphaned uploads after a kill, and a done check for at-least-once delivery.
- Added the page status endpoint and polling, and the enqueue-failure handling.
- Kept the fixed facts: 10,000 row threshold, replica only, report.view, 24-hour link, send_email, no cleanup job, 512 MB, 2 million rows, 1800 s timeout, failure email, out-of-scope list.
- Added open questions: unmeasured timeout, undecided poll interval and template names, no permission recheck in the job.

### Holes
- None.

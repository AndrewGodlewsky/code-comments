## Review of feat-01 (rewrite-v5, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Rewrote in the required order: summary (with how the page works today), terms, numbered run steps, failure table, build/verify section, open questions.
- Added a Terms section defining read replica, report.view, row_count, keyset paging, shared row query, job queue, multipart upload, exports bucket, signed_url, send_email and the report_exports table, each in plain words.
- Moved the Assumptions section into the build and verify section as a short confirm-before-building list.
- Merged the Data model section into the terms, kept the table and the two indexes, and dropped the index naming detail.
- Merged old step 12 and the failure-injection details into one short checks list, separate from how the system runs.
- Merged step 6's separate done and failed checks into one early-return rule.
- Moved the lost-enqueue repair (stale queued row with no job_id) from step 5 into step 4 where it runs, and kept a pointer in step 5.
- Cut the query-count estimate for the small path, the 'at most about 20 queries' line and some repeated explanations of why retries are safe.
- Added a single failure table summarising every step's failure case.
- Added short reasons where a newcomer would ask why: why two paths, why the click copies filters from the URL, why done is set last, why the link is created just before sending.
- Removed the cross-step codes in the text where possible, and kept plain step numbers only for flow pointers.
- No change to the plan's intent or mechanisms.

### Holes
- None.

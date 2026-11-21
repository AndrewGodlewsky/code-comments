## Review of feat-01 (junior-v4, author sonnet, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Step 3 reordered: select the active export first, handle orphans there, then insert, and fall back to select if the insert race is lost. This fixes the contradiction with step 4.
- Step 4 now sends the 202 only after enqueue and saving job_id, and states what the client sees if enqueue fails. The orphan wording points to step 3.
- Vocabulary: added report_rows and reports.row_count (unfiltered total), ctx, and on_final_failure.
- Step 1: noted that row_count is unfiltered, so a filtered view of a large report still takes the large path.
- Step 6: added a note on concurrent delivery and its harmless worst case. Added a matching open question.
- Step 5 and step 9: said that a killed attempt leaves the row as running through the retry wait, and that step 6 then aborts the old upload.
- Step 8: expires_at is set when the row becomes done. The email link TTL is the time left until expires_at, so the emailed link and the page link end together. The duplicate email now has the same expiry.
- Step 7: added a consistency note and said a replica failure mid-read is an ordinary attempt failure.
- Step 11 and the tests: wording aligned with the above (24 hours after done; the orphan is re-enqueued on the next click).
- Step 5: named the download endpoint (GET .../exports/{export_id}/download) and what it checks and returns; added export_id to the latest response.
- Step 6: failed status returns without raising; access removed now calls fail_export and returns, skipping retries, instead of deferring to the final-failure step.
- Step 10: reframed as the shared fail_export helper, called by on_final_failure and by step 6.
- Step 3: stated that a row with a job_id is never an orphan and that a click during a retry wait returns the existing export.
- Step 1: added how the page tells the 200 CSV from the 202 JSON.
- Step 2: stale-count fallback now counts rows while reading, stops at 20,000 in the same request, and the query budget is corrected to 40.
- Vocabulary: added fail_export, the storage helpers and send_email with a note that their errors are undocumented; added a matching open question.
- Steps 7 and 8: count rows while streaming, set row_count_written from that count, and say what to do when the done update matches no row.
- Tests: added access-removed and retry-wait cases.
- Step 9: the handled-failure update now has WHERE status='running', so a done or failed row is never reset to queued (Q17).
- Step 8: the email-failure case says the row stays done and the retry goes to the email; added that step 8 can also start from step 6 finding done (Q17, Q18).
- Step 6 item 2: now the single branch point for failed, done and queued/running; done skips the re-check, abort and upload and goes to step 8 item 2 (Q18).
- Step 6 item 5 and step 0: the job also writes job_id=ctx.job_id when it starts (Q20).
- Step 4: added the failure case where enqueue succeeds but saving job_id fails (Q20).
- Step 10: reordered so upload_id and notified_at are read before the update clears upload_id, then abort, then email (Q19).
- Tests: added an email-failure test.
- Step 8: reworded the duplicate-delivery sentence about rewriting the file, since a done row now never reaches the upload steps.
- Reordered into the newcomer layout: summary with how the page works today, terms, numbered steps each with starts/does/state/failure, then build and rollout, then open questions.
- Moved the old Step 0 (table, unique index, email templates) and the tests into a separate 'Build and rollout' section, apart from how the system runs.
- Merged old steps 3 and 4 (find/record the export and queue the job) into one step 3, and merged the three enqueue failure cases into it. Steps renumbered 1-9.
- Folded old step 11 (link expiry and cleanup) into a short closing note and into the page-state step; removed it as a numbered step.
- Changed the stale-count safeguard from a 20,000-row stop to a simpler 10,000-row stop, so there is one threshold.
- Cut the 1,700 s clock check in the job, since step 5 already aborts a previous upload and the queue timeout retries anyway.
- Cut the long paragraph about two attempts of one job running at once from step 5 and left a one-line note in open questions.
- Cut repeated explanations of done/notified_at handling (stated in steps 5 and 7 only) and the repeated 'retry wait shows queued or running' notes.
- Removed cross-reference codes in the prose where a plain statement works, and shortened the terms list by dropping the export-row and ctx duplication.
- Shortened the table column descriptions and merged the time and memory notes into one line each.

### Holes
- Q4: If the queue delivers the same job twice at the same time, while the row is queued or running, what stops two attempts from writing at once? Step 6 only handles done or failed. (author: jobs.py says only that a handler may run again for a job that already succeeded. It does not say whether two attempts of one job can run at once, and I do not know. Step 6 assumes not. If it did happen, both attempts write identical content to the same key, so the worst case is a wasted retry. I added a short note in step 6 and one line under open questions, and added no lock because the brief does not require one.)

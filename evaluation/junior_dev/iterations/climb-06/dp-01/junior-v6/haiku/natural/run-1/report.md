## Review of dp-01 (junior-v6, author haiku, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Restructured the document into the required order: summary, terms, diagram, steps, failure table, build and rollout (kept separate from how it runs), and open questions.
- Added a terms section that defines the lock, cutoff, window, lookback, staging, merge, hwm, etl_watermark and etl_run_log in plain words.
- Defined the pipeline lock (Q1): a row in etl_lock, a committed write on take, a wait-and-check rule for a second attempt, release at commit or in the failure path, and no expiry rule, with on-call clearing a stuck lock.
- Defined the attempt timeout (Q2): the scheduler stops the attempt, the open transaction rolls back, and the normal failure path runs. The timeout length is listed as open.
- Step 1 now writes the run log row as running as a committed write, so failed attempts stay visible after rollback.
- Step 9 now sets committed_at and last_committed_run_id, and states that staging is dropped after commit.
- Added the late-commit follow-up to #data-alerts (Q8). It is posted by the job itself when its commit is after 06:00 UTC, and it is shown in the diagram and failure table.
- Made the failure path explicit for validation failures and timeouts (Q6). Failed validation now appears in the diagram and table, and it states that nothing partially loads.
- Added the first-run full extract to step 2 and the cutoff-null failure to step 3.
- Reconciliation: added the created_at filter for creation days, the wait for the next committed load if Sunday's load fails, and that the reload is an upsert that never deletes. Connected the reconciliation's alert node to its next-day node in the diagram.
- Diagram: added the etl_lock node, the run-log writes, and the late follow-up. Quoted labels that contain special characters. Replaced the separate subgraph state notes with arrows to the state tables they read or write.
- Dashboards (Q9): stated that dashboards show the last committed night, which is the previous night's data while tonight's load is pending or has failed.
- Cut repetition: merged the retry, timeout and lock notes into one retry paragraph and one lock paragraph, and removed duplicate statements about the read-only replica.
- Kept every stated fact from the brief and the first version: the 02:00 start, read-only replica, updated_at and deleted_at rules, the 90-minute bulk-import bound, the 2-hour lookback, one row per order_id, hwm advancing only after success, three attempts 15 minutes apart, the page after the third failure, the 06:00 dashboard refresh and staleness alert, the Sunday reconciliation for 30 days with count and checksum, the reconciliation reload, the swap fallback, the window and cutoff reasoning, and all six assumptions. The window reasoning is still marked as untested.
- Step 4 now reads the extract in batches and says a row can come back twice; step 7 handles that (Q10).
- Step 7 now runs as the first part of step 8, and step 8 opens the warehouse transaction (Q10, Q11).
- Steps 1 and 5 now say their writes commit on their own, outside the warehouse transaction (Q11).
- Added the night column to etl_run_log and defined a night as the UTC date of its 02:00 start (Q12).
- Counting rules added: retries copy the night, a manual rerun names its night, a failed rerun counts, and a rerun after the page is allowed (Q12).
- The scheduler now owns the retry timer; a host death counts as a timed-out attempt; the diagram's retry node and failure text were changed to match (Q15).
- Added a warehouse-unreachable row to the failure table and an open question about the count (Q15).
- Added a manual rerun entry point to the diagram (Q12, Q15).
- Reconciliation reloads take the pipeline lock, and a lock timeout stops reconciliation until next Sunday (Q13).
- Added a first-run note: window starts at the configured start date, runs as one attempt, and sets hwm to the cutoff (Q14).
- Rewrote the replay-timestamp reasoning so that the row's commit is after the cutoff and its updated_at is later than the cutoff minus 90 minutes. The meaning is unchanged.
- Reorganized into summary, terms, diagram, notes, steps, reconciliation, failure table, build and rollout, and open questions. Added a 'starts after' line to each step. Kept every stated fact from the brief and the first version.
- Cut the stray opening sentence of the summary, 'The job does not change an existing job.', which says nothing about the pipeline.
- Merged the first version's two overlapping sections, 'Notes' and 'Rules the steps rely on', into one set of rules. The window and lookback reasoning, the lock, retry counting, the first run, and the dashboard and 06:00 check each now appear once.
- Reordered the document to the skill's layout: summary, terms, diagram with notes after it, steps, rules, failure table, build and rollout, open questions.
- Gave each of the nine steps the same four parts: what starts it, what it does, what data it keeps, and what happens when it fails. The first version had these spread across a prose note and a separate list.
- Added one-line definitions for terms the first version used without defining: pipeline lock, etl_lock, etl_run_log, anomaly, night, attempt, run id, replay timestamp, cutoff, lookback, bulk import, watchdog, attempt timeout, checksum, dashboard views, and warehouse transaction.
- Added the reason for each part, in one short clause where it appears: the 2-hour lookback, the separate staging table, the single warehouse transaction, the newest-row step before the merge, the replay-time cutoff, the lock, and the scheduler owning the retry timer.
- Step 4 now says the extract is read in batches and that a row changing between batches can come back twice. The first version said it was one read, which contradicted the dedupe step.
- Step 1 now says the lock is a committed write, that waiting attempts check once a minute, and that a timeout while waiting counts as a failure. The lock still has no expiry rule, because the brief does not require one.
- Added the etl_lock table to the terms and the diagram. The first version named it only in the state notes and the answers.
- Stated the night column and the counting rule explicitly: a night is the UTC date of its 02:00 start, and the count is the failed rows for that night. A manual rerun defaults to the latest 02:00 start.
- Stated that the reconciliation takes the pipeline lock for each day it reloads, and stops with an alert if it cannot get the lock within the attempt timeout.
- Added a failure-table row for 'Sunday load does not commit', which was stated only in the text before.
- Moved the swap fallback from the notes into the rules, and stated that the rest of the flow is unchanged. Kept the assumptions list under build and rollout.
- Checked the first version line by line. No stated requirement, limit, number or rule was dropped. Every 2-hour, 90-minute, 15-minute, 06:00, 02:00/02:15/02:30, 30-day, 3-attempt, and 2^64 value, and every failure-table row, is still present.
- Step 1 now writes the running etl_run_log row before it tries the lock, so a waiting or timed-out attempt has a row the scheduler can mark failed (Q16, Q20).
- Step 9 marks the run log row committed only if it still says running, in the same transaction; otherwise the commit is refused and rolls back (Q16).
- Added the section Stopping an attempt that times out, with the scheduler's four steps in order: conditional failed write, stop job and end sessions, clear lock for run id, retry after 15 minutes (Q16, Q17).
- Changed the watchdog check from etl_watermark.committed_at to a committed etl_run_log night row for tonight, so a rerun for an earlier night cannot pass the check (Q19).
- Added the Manual reruns section: same window from the current hwm, the named night only sets failure counting, reruns for committed nights are allowed and harmless (Q18).
- Stated that the lock wait counts toward the attempt timeout and who usually holds the lock (Q20).
- Diagram: step labels updated, the watchdog reads etl_run_log instead of etl_watermark, and the roll-back node logs failed only if still running.
- Failure table: added a row for a commit refused because the run log already says failed; the timeout row now points to the stopping steps.
- Restructured to the skill's order: summary, terms, diagram with notes, steps, failure handling, open questions, with build and rollout kept separate. Defined the new terms warehouse session and upsert. Every stated fact from the first version was kept.

### Holes
- Q5: In step 5, what does 'bulk load' do and how does the extract get from the replica into the warehouse staging table? What tool or process runs this? (author: The ETL job runs the extract (step 4) and the bulk load (step 5). It reads rows from the replica and passes them in batches to the warehouse's bulk-load facility, which writes into stg_orders_RUN_ID. The brief names neither the warehouse nor a bulk-load tool, so the exact tool and file format are not known. They are listed in open questions.)

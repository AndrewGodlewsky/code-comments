## Review of dp-01 (junior-v6, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Restructured into summary, terms, flowchart, then steps, failures and open questions, and added a terms section.
- Q1 and Q3: stated that the scheduler owns retries and runs attempts one at a time; crash, hang or timeout counts as failed, with a HANG node in the diagram.
- Q4: defined run_date as the scheduled UTC date shared by all attempts, and said the watchdog matches on run_date and kind.
- Q5: said the job counts rows read in one replica query and compares them with staged rows for the run; the label in the diagram now says so.
- Q6: explained why the 2-hour overlap on the next night covers late-visible rows.
- Q7: reconciliation is now a second phase of the same job with its own reconcile run row; replaced the retry arrow into the nightly retry with a separate reconcile retry that reruns reconciliation only.
- Q8: changed staging cleanup so every attempt and reconciliation empties staging first and deletes its rows in the merge transaction; the old per-run_id cleanup could not clear failed attempts.
- Q2: stated that nothing stops an attempt past 06:00 and added attempt timeout and run time to open questions.
- Added a failure table and moved the assumptions into open questions; kept every original fact.
- Reworded the intro and reconciliation step 5 to give both reasons a day can mismatch (late-visible rows beyond the overlap, and harmless writes after the cutoff), fixing the contradiction.
- Added that the scheduler kills a timed-out job and waits for it to end before the next attempt, and pages if it cannot confirm.
- Added that the scheduler judges an attempt by the etl.run status, so a crash after commit is not retried; added a JUDGE node to the flowchart and a failure-table row.
- Stated that the first run loads everything from the seeded start time in one query, with no separate backfill.
- Folded dedup into the merge query and removed the separate DEDUP flowchart node; stated that zero rows read matches zero staged.
- Clarified how soft-deleted rows and which updated_at are used in the reconciliation count and checksum.
- Added the stalled-replica case (cutoff below the HWM): the window is small or empty and the HWM stays; added a failure-table row and two open questions (no lag alert, first-night size).
- Updated the Scheduler term to include killing on timeout, and the staleness note to say only the timeout stops a running attempt.
- Reordered into summary, terms, flowchart, then steps, failure table, rollout, open questions; the diagram keeps its form with summary and terms before it and notes after.
- Merged the earlier 'Steps and where state lives' headings into one 'How it runs' section with sub-sections (tables, what starts what, extract window, staging and merge, why safe, staleness, reconciliation).
- Added a 'Setup and rollout' section holding the seed and first-night backfill, kept apart from how the system runs.
- Added a failure-table row for 'scheduler cannot confirm a killed job has ended' (no new attempt, page on-call), which was only in the steps before.
- Merged repeated statements: retry ownership and 'only scheduled start' folded into the start steps; trimmed repeated explanations of idempotence and watchdog matching.
- Dropped the sentence on the watchdog matching 'same date the 02:00 start had' since the run-date term now says it; kept all stated facts (2h lookback, 90 minutes, 30 days, 15 min x3, 06:00 alert, #data-alerts, one row per order_id, is_deleted, monotonic HWM, assumptions).
- Clarified that wh.orders is changed only by the merge transaction and that the job only runs one attempt while the scheduler owns retries.
- Left out per the skill: exact bulk-copy tool and first-night size handling remain open, not designed.

### Holes
- Q2: What do the retries mean for the 06:00 watchdog? Attempt 3 could start at 02:30 or later. What is the longest a run takes, and does anything stop an attempt that is still running at 06:00? (author: The longest run time is not known, so I cannot say whether attempt 3 can pass 06:00. Decided: nothing stops an attempt at 06:00. If it commits later, the data appears then. The watchdog alert fires meanwhile and dashboards show the previous committed state. Added to open questions.)
- Q5: What does the extract do when it has to pull rows from the replica into the warehouse? What tool or mechanism moves them, and what is 'extracted count' compared against? (author: The brief names no copy tool. Mechanism: the job runs one query on the replica, counts the rows it reads, and bulk-loads them into staging. The staged row count for this run_id is compared to the rows read. Which tool does the bulk copy is not decided and is listed as open.)

## Review of dp-01 (junior-v2, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Merged the "Orchestrator" and "scheduler" into one Scheduler node, and added a Components section naming the scheduler and the pipeline job (Q1).
- Added lock lease rules: lease equals the 45-minute deadline, the lock is released on commit or failure, and a retry that finds the lock held is logged skipped without counting as an attempt (Q2).
- Added the first-run watermark seed and the window it produces (Q3).
- Added an explanation of why the 2-hour lookback exists and how replica lag is covered (Q4, Q5).
- Removed the undefined "sane row count" from validation and moved it to open questions (Q6).
- Narrowed merge step 2 to this run's staged order_ids and explained when it can fail (Q7).
- Defined the staleness check as any success with committed_at at or after 02:00 UTC today, ignoring failed attempts, and made an unreadable warehouse alert (Q8).
- Removed the separate "process dies after COMMIT" case because the success log row is inside the commit transaction, which contradicted merge step 4.
- Changed the reconciliation reload to run merge steps 1 and 2 only. The old wording, "same guarded MERGE", would have moved the watermark to the Sunday cutoff.
- Routed reconciliation errors to a reconciliation-only retry instead of the nightly FAIL path, because the night has already committed and must not be rolled back.
- Replaced the "Orchestrator timer" wording with the scheduler timer, and merged repeated retry and dashboard text to keep the file short.
- Scheduler now creates run_id and attempt number and owns failure handling: it writes the failed row, drops staging, releases the lock, counts attempts and pages. A crashed job cannot write its own failure (Q10, Q14, Q15).
- Scheduler releases the lock on failure, so a retry 15 minutes later does not find a stale lock (Q14).
- Failed row is written only if no success row exists for the run_id. No retry or page happens once a success is committed tonight, which covers a commit just before the deadline stop (Q10).
- Reconciliation is its own job with its own lock and 45-minute deadline. Its attempts are counted apart from nightly attempts (Q9).
- Extract stated as one query and one bulk load into staging. Replica errors and slowness are covered by attempt failure (Q11).
- Deleted-order path explained in the merge section, from the brief's rule that every write sets updated_at (Q12).
- Stated the case where cutoff is not later than the stored HWM, and what the run does (Q13).
- Merged the duplicate failure and retry text into one section, cut repeated component notes and the duplicate who-starts list, and kept the file close to its first length.
- Added two open questions: whether the warehouse rolls back an open transaction when the job's connection drops, and what happens when the scheduler cannot write to the warehouse.
- Merged the Components section's scheduler and reconciliation descriptions, so reconciliation is now its own listed component and the 'Who owns each attempt' section is folded into Components and Failure.
- Folded 'What starts each step' and 'Where data moves' into one short 'Triggers and data moves' section, with no repeated bullets.
- Cut the duplicated scheduler-releases-lock statement from the Failure section, since the Lock section now states it once.
- Merged the 'cutoff not later than stored HWM' edge case into the Window and HWM section as one bullet, next to the HWM rule it qualifies.
- Shortened the first-run and replica-lag bullets to their essentials and removed the repeated explanation of why the lookback is 2 hours from the Failure section.
- Flowchart: merged the two failure paths into one FAIL node, removed the duplicate 'drop staging, release lock' nodes after COMMIT, folded the two reconciliation failure branches into one RFAIL node, and shortened long labels. The flow of the main path, retries and paging is unchanged.
- Consolidated the separate 'Assumptions and open questions' list into one 'Open questions' section at the end, with the 'leftover staging' note moved into State.
- Kept all of the brief's fixed requirements, the merge logic, the staging design, the HWM storage and update rule, and every open question. No behaviour was changed.

### Holes
- None.

## Review of mig-01 (junior-v7, author haiku, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a Terms section (source of truth, target, pending, tombstone, sweeper, comparer, advisory lock, write_mode values, read_from_pg) so the rest can use plain words. Q1, Q2, Q3.
- Split the file into how the system runs (writes, sweeper, backfill, comparer, reads, freezes) and the rollout checklist, with a failure table for runtime failures. Q2, Q4.
- Moved the pending row into the same MySQL transaction as each change, so a crash cannot lose the copy. Q4.
- Made pending rows carry an op (copy or delete) and added tombstones on both sides. The erasure delete writes a tombstone and a delete pending row, and the sweeper applies it on the other side. Required by the brief's no-reappear rule. Q5.
- Added an advisory lock per user id on the target, so a copy and a delete of the same user cannot interleave. Required by the brief's no-reappear rule. Q5.
- Defined the backfill batch: one Postgres transaction that copies rows and saves last_id, with a 5-second lag pause and crash resume from the last completed batch. Q5.
- Moved backfill_progress to Postgres only, because it must commit with each batch. The first version listed it in both databases; this is a change. Q1, Q5.
- Defined the comparer's clean rule (every column incl. version, tombstones skipped, 60-second re-check, zero confirmed mismatches) and made repairs go through pending rows. Q6.
- Defined read routing per user with flags.enabled_for, a 200 ms Postgres timeout, and fallback to the MySQL replica so reads never fail. Q7.
- Replaced the vague freeze with a frozen write mode, a 30-second cache wait, a 40-second check, and a bounded worst case of about 75 seconds under the 90-second limit, with an abort path before the new mode is set. Q8.
- Set the Postgres id sequence to MySQL's AUTO_INCREMENT value read during the freeze, so no id is reused. Q8.
- Added a rollback procedure (reads to 0, freeze, drain, AUTO_INCREMENT check, back to mysql_primary) and stated what is switched back. Q9.
- Added a step to remove the MySQL code paths after pg_only and the drop. This step is new.
- Kept every requirement and step from the first version and the brief. Gates are stated for the switch to pg_primary (3 days at 100%, clean comparer, empty pending) and pg_only (14 days, empty pending, clean comparer).
- Added open questions: who may change the flags, a never-clearing email clash, a permanently failing backfill row, backup retention, the starting timeout values, and ramp hold times. These are unknowns, not invented reasons.
- Restructured into the junior-dev layout: summary, terms, how it runs, rollout checklist, rollback, failures, open questions. Each rule now appears once; the duplicate failure text in the writes and sweeper sections was removed in favour of the failure table.
- Terms: added `version` (who increments it, copies keep it), replica and replica lag, backfill, id sequence (AUTO_INCREMENT), and the `frozen` use during switches and rollbacks (Q10, Q15).
- Writes: every delete writes a tombstone and a pending row, since `UserRepository.delete` is the only delete path (Q11).
- Ids: the copy keeps the source's id in both directions, so each user has one id on both sides (Q15).
- Sweeper: stated that both delete-row steps are repeat-safe, and that the sweeper keeps the previous source during a freeze so pending rows drain (Q12, Q14).
- Freeze: added a 15-second limit on switch work, so the pause is at most 85 seconds under the 90-second limit, and a rule to set the old mode back if the work overruns. The original 75-second figure assumed unbounded switch work (Q12).
- Freeze: stated why writes are frozen and that paused writes get a retryable 503 that clients already retry (from the brief).
- Drain: zero is checked by a query of the MySQL primary's `pending` table, not the replica (Q12).
- Checklist: named who changes each flag and who watches the metric; backfill, sweeper and comparer are automatic (Q13).
- Comparer: starts after backfill, runs until the MySQL table is dropped, keeps running during freezes, and the 60-second re-check clears in-flight writes (Q16).
- Sweeper: stated that Postgres misses are repaired automatically, with no manual step (from the brief).
- Failure table: added a row for switch work overrunning 15 seconds or MySQL pending not reaching zero.
- Open questions: kept all six, and added the 15-second switch-work limit to the list of starting numbers.
- Summary cut to three sentences: how it works today, the main flow, and why it is shaped that way. The context numbers were not in the brief, so they were not added.
- Terms: kept every term and added one-line definitions for names a newcomer would not know: retryable 503, `frozen`, `flags.enabled_for`, `jobs:dead`, and the two advisory-lock functions. Each flag value is listed once, under `users.write_mode`.
- Split the content into How the system runs (writes, sweeper, backfill, comparer, reads, switches and freezes), the Rollout checklist, Rollback, the failure table and Open questions, so each rule is stated in one place. Rollout steps now refer to the freeze section instead of repeating it, and the switch work for step 8 is stated once.
- Every rollout step now has what starts it, what it changes, where its state lives and what happens if it fails. Steps 5, 9, 10 and 11 gained a short failure line. Step 11's failure line points to a new open question.
- Added one open question: what code from before step 11 does when the flag is pg_only, because a rollback of that deploy could write to MySQL. The brief does not answer this.
- Rollback: reworded 'Only the two flags change' to allow for the AUTO_INCREMENT check in step 4, and noted that the sweeper drains Postgres pending while frozen.
- Kept every number and rule from the brief and the first version: 2,000-row batches, 5 s lag, 200 ms copy and read timeouts, 100 rows per sweep, 10 s sweeper interval, 60 s re-check, 30 s flag cache, 40 + 15 + 30 = 85 s freeze budget under 90 s, 3-day and 14-day holds, the 1/10/50/100 ramp, the drop-to-0 reversal, the backup-before-drop rule, the tombstone and version rules, and every failure-table row and open question.
- The first version's checklist items are all covered by the rollout steps. Each is cross-checked against the text.
- Sweeper section: stated that the sweeper runs in every mode and never reads the mode, and that the table a row sits in gives its direction (answers Q18, Q23).
- Writes in mysql_primary, step 3: added that a copy which lands but cannot delete its pending row leaves the row for the sweeper to repeat harmlessly (Q17).
- Rollback to MySQL, step 3: said the sweeper copies Postgres pending rows whatever the mode is (Q18).
- Rollback to MySQL, step 4: the AUTO_INCREMENT check now covers every id on either side, and says why the counter normally holds (Q19).
- Freezes and switches, Ids: the Postgres sequence is set to the larger of MySQL's counter and its current value, so it never moves backwards (Q19).
- Comparer section and rollout step 8: the switch reads the latest completed pass, so a pass still running does not count (Q22). Rollout step 10 uses the same wording.
- Rollout step 8: says the MySQL pending check is a query of the primary, not the replica, and that a running pass does not count (Q22).
- Failure table: the email-clash row says the copy writes every column and the refusal happens on the target (Q21).
- Failure table: added a row for the same version with different content, which the comparer reports (Q20).

### Holes
- None.

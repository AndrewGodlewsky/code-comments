## Review of mig-01 (junior-v5, author haiku, natural)

Rounds: 4. Ended: teachback-correct.

### What changed
- Restructured the document into a summary, a terms list, a how-the-system-runs section, the rollout checklist, a failure table and open questions. Each step now says what starts it, what it does, where its state lives and what happens if it fails.
- Stated that the write fence covers writes only, and that reads are never fenced (answers Q1).
- Defined the forward outbox worker: every 1 s per instance, up to 500 rows per pass, read-first ordering, deletes only up to the noted seq, and no-op when the MySQL row is gone because erasure already handled it (answers Q2, Q3).
- Wrote outbox rows with every user write from the deploy step on, not only when dual writes are on. The old text said writes in the gap were not in the outbox, which contradicted the shared mechanism.
- Defined version, its source and its increment, and noted that the Postgres write path must add 1 after the switch (answers Q4).
- Added the backfill lease (owner token, 60 s, conditional checkpoint update) and defined `last` (answers Q5).
- Replaced the step 6 rule that the outbox must be empty with a deferral rule. The old rule could never pass under normal traffic (answers Q6).
- Defined the sampled read comparison in the move-reads step, including the metric and the rule for pending outbox rows (answers Q8).
- Explained in the switch step how instances switch modes and why 503 retries are safe (answers Q7).
- Shortened the rollback step to refer to the switch and reverse path, and kept its pause budget and abort rule.
- Listed the unwritten post-switch erasure and reverse-direction deletes as open questions instead of inventing a mechanism.
- Removed ordinary delete from the dual-write step. Delete is erasure-only, per user_repository.py, and erasure has its own step.
- Added the erasure work list and the sweeper to the terms and to step 3. Stated why the Postgres tombstone step runs from step 2 onward, before dual writes.
- Moved the control row and erasure work list to Postgres at the switch, with a write-order rule for mode changes. Instances read the store that holds the source of truth. Fixed the MySQL-down-after-switch failure row.
- Made the lease count from when the poll was sent, and added the derivation of the 12 s drain wait.
- Defined when the forward worker runs (dual writes on, and paused) and when it stops (mode pg). Explained why in-flight copies are harmless.
- Step 7 sampled comparison now checks users_pg_outbox for the user before counting a mismatch. Added a stale-read row to the failure table, and an open question on read-your-writes.
- Step 10: defined reverse erasure with the target-first order, and the unique-email conflict retry rule.
- Step 11: rollback now checks that every Postgres tombstone exists in MySQL before resuming writes. Pause writes go to the store the instances read, and the abort step writes to Postgres first.
- Replaced the vague 'next-but-one step' wording in step 9 with a reference to step 11. Step 5 now says why tombstones protect backfill from erased users.
- Step 9.4: the pg mode write to Postgres now copies the erasure work list into Postgres in the same transaction, keeping each row's state, and says a half-done row finishes after the switch in reverse order (Q16).
- Step 9.4: says instances keep polling MySQL and stay paused until they see pg there, so they switch only after the MySQL write lands (Q17).
- Where the control row lives: added that a switch in progress leaves instances on the old store until they see the new mode, so a pg written only to Postgres leaves every instance paused (Q17).
- Terms, erasure work list: added the three row states (not started, half done, done) so later steps can refer to them (Q16).
- Step 3 Starts: the work list lives in the store that holds the source of truth, and a sweeper on every instance runs on a timer, fenced like other writes (Q18).
- Step 3: added the half-done state, which a pause or crash can leave behind, and pointed it at step 9 (Q16, Q18).
- Step 4: the request waits up to 200 ms for the inline copy before it returns. The inline copy does not delete its outbox row. Only the forward worker deletes outbox rows, so one path does (Q19).
- Control-row paragraph: a pause is written only to the store instances read now (MySQL before the switch, Postgres during rollback), and a mode change goes to the store instances are moving to first.
- Step 9 failure path split by which control write has landed (nothing in Postgres yet; Postgres has pg but MySQL does not; MySQL has pg and instances applied it), so the step 11 pause no longer goes to the wrong store.
- Step 9.4: the sweeper's remaining part for a half-done erasure row is now stated as the MySQL part (tombstone, row delete, mark done).
- Step 8 and step 9 start conditions: a full compare must run during the hold, after the latest clock start, and finish clean.
- Forward worker section: run conditions stated (mode paused, or mode mysql with users.dual_write on); stops in pg and pg_only.
- Reverse worker: run and stop conditions stated as its own section.
- Step 10: state line added (pg_outbox and erasure work list in Postgres).
- Step 11: pause written to Postgres; erasure work list copied back to MySQL; reverse worker stops at the drain; dual_write flag stays on; abort path restarts the reverse worker and is limited to before step 4 is applied.
- Failure table: added a row for a switch that stalls with pg in Postgres only; the control-row row now points to step 9.
- Terms: dual-write flag and erasure work list defined; erasure work list copy at rollback noted.
- Summary: now says how the system works today (MySQL primary for writes, replica for reads, MySQL as source of truth) before the plan, and lists the phases in one flow.
- Terms: defined the MySQL primary and replica by name, defined 'lease', 'write fence', 'version' (set by the app, not the database), 'erasure', 'backfill' and 'sweeper' in plain words. Stated that erasure is the only delete path (answers Q10).
- Terms: merged the separate 'Replica lag' and 'Erasure work list' entries into the terms they support; cut the duplicate 'Mode' explanation that repeated the steps.
- Write fence: stated that the mode is read directly from the control row, not the 30 s flag cache. Kept the 12 s derivation (Q12) but shortened it to the chain of times and the one margin. Added that a failed poll stops writes only, not reads (Q1).
- Control row: merged the two rules into one short list and stated the switch and rollback write order with the reason a plain pg write leaves instances paused (Q17, Q20).
- Forward and reverse outbox workers: moved them into 'How the system runs' with their run and stop conditions in one place. Added that a failed copy leaves the row for the next pass (Q2, Q13).
- Step 2: removed the repeated list of switches; kept the rule that the lint rule is not widened silently.
- Step 3: kept the order (a) then (b) and the reason for running it before dual writes. Added that the sweeper runs on every instance, reads the work list of the store that holds the source of truth, and is fenced (Q11, Q18). Added one line on why the job queue is not used.
- Step 4: stated that the inline copy runs before the response, that the forward worker alone deletes outbox rows, and the cost of about 400 rows (Q19). Erasure is named as not on this path.
- Step 5: defined 'last' as the checkpoint, and said how the lease and token check prevent a stale runner from committing (Q5).
- Step 6: replaced the 'outbox must be empty' rule with the defer-then-recheck rule and the clean-pass definition (Q6). Kept the reason the outbox-empty test would never pass.
- Step 7: defined the sampled comparison fully (who runs it, what it compares, how a mismatch is counted and reported) (Q8). Kept the accepted stale-read behaviour and named the outbox check (Q14).
- Step 8: stated that a compare must start after the latest clock start and finish clean during the hold, and that pending-outbox rows are deferred (Q22).
- Step 9: merged the failure branches so each one names which store has pg and what to do (Q16, Q20). Stated why 503s are never applied and that half-done erasure rows finish in MySQL after the switch. Clarified the start conditions and the pause budget.
- Step 10: stated the reversed erasure order and the unique-email conflict rule (Q15). Added the id-counter note.
- Step 11: kept the write order, the tombstone and AUTO_INCREMENT checks, and the rule that abort is impossible once step 4 has applied. Stated that the dual-write flag is not changed (Q21).
- Failure handling: merged the per-section failure notes into one table and kept the per-step 'if it fails' lines. Removed the repeated rows that appeared twice.
- Open questions: kept the three items, and removed the open question about reverse deletes, which is now answered in step 10 (Q15).
- Cut: the repeated explanations of why each step is safe, when they were already stated once in the mechanism sections; the repeated 'writes return 503' lines; and detail about the forward worker's internals that a newcomer does not need to follow the main flow.
- Length: the rewritten file is shorter than the first version, with the same steps, the same brief requirements and the same failure cases. No brief requirement was changed. No codes such as R3 or Q7 remain in the text. The only cross-reference left is to numbered steps in the same file.

### Holes
- None.

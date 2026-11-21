## Review of mig-01 (junior-v3, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a 'What this is' summary and a Terms list defining owner, fence, version, outbox, copy, version rule, tombstone and lease.
- Added 'Where the code runs' (Q1) and 'A write in phase A' as a numbered flow, which shows the read-back, applied_version and the fence-after-commit reasoning (Q2, Q4, Q5).
- Replaced the six mechanisms and the state inventory table with the Terms list, the write path, the Erasure section and per-step State lines. Removed the duplicate inventory.
- Dropped the op column. A missing source row is now handled by a tombstone check in the sweeper (Q3).
- Rewrote erasure as a pending user_erasures row, two steps, with step 2 in one transaction, so no partial state exists (Q9).
- Fixed phase B erasure order in step 10, which previously called the MySQL delete last. Erasure in phase B now writes the MySQL tombstone and copy delete first, then the Postgres row delete in one transaction.
- Removed epoch and owner_since from users_control. mode is set to pg_reverse at step 9 and pg_only at step 11 (Q8).
- Fixed step 2's expectation. With dual write off, the outbox does not drain by itself. The sweeper must keep up with peak writes.
- Moved leases from a MySQL migration_state row to Postgres session advisory locks, so a crash releases them and phase B needs no MySQL lease.
- Step 4 now also sets the users.write_owner fallback flag to pg, so writes can reach Postgres if MySQL is unreachable after the commit point.
- Rollback: step 6 now also sets Postgres owner to mysql (previously Postgres was left paused with no next step). Step 7 restarts the forward sweeper and sets users.dual_write back to 100.
- Standing rule on repair now says the source database's primary, since the source is Postgres in phase B.
- Renamed step '10R' to 'Rollback' so the document has no codes that point elsewhere.
- Merged the 90 s budget breakdown from Open decisions into step 9. Kept the measurement and the 80 s abort as open questions.
- Added open questions: client retry duration (Q6), stale fallback reads in phase C, the erasure trigger (Q9), the int4 advisory-lock key limit, and the outbox-age alert threshold.
- Added the phase B write path as its own short section, because step 10 and Q11 both depend on it.
- Defined the routing rule: every write reads the MySQL control row first and rolls back if it says pg. Routing does not use a flag, because flags can be stale. Recorded this under Terms.
- Defined users.write_owner precisely: it is used only when MySQL is unreachable, it is set to pg at step 9 commit and back to mysql at the rollback commit point. Rollback step 6 now sets it, which was missing before.
- Added queued_at to the outbox so the sweeper can take the oldest rows first and the age alert has a defined source. Recorded the sweeper's batch size and order in step 2.
- Made the backfill gate automatic: removed the person confirmation, and the gate is written after the conditions hold for two minutes. Recorded the open question about how build versions are reported.
- Added a resume rule to the switch (step 9) and rollback so a job that dies after its commit point finishes the MySQL or Postgres update. Without this, the state after a crash was unclear.
- Made the dual-write flag explicit: it is a percentage bucketed by user id, and 100 means every write tries the inline apply.
- Step 7: read-path error and fallback counters are named, the gate is zero new errors and zero confirmed mismatches, and a person sets the next percentage. This replaces the vague 'mismatch spike'.
- Stated in step 4 of the write path that the inline copy is not cancelled at 200 ms, and why a late copy is safe.
- Shortened some sentences and removed repeated wording in the steps and standing rules. Kept every step's starts, changes, state and failure handling, and kept the intent of the brief.
- Merged the 'What this is' summary and the phase list into one opening section of two short paragraphs.
- Moved the standing rules into a short 'Rules that always hold' list under Terms, and folded 'Where the code runs' into one paragraph there, so the rules are not spread across the file.
- Cut the repeated explanation of the fence and outbox in the phase A write: the fence release is explained once, after the write steps, and the 'step 4 never fails the request' sentence is kept only once.
- Merged the phase A and phase B write paths and the erasure section into one 'How a write works' section, placed before the steps, with the erasure sub-steps kept in full.
- Shortened the Terms: each term is one or two lines, and the lock, tombstone and lease definitions are kept with their mechanism only.
- Step 6 now says the repair runs through the outbox, so the repair method is visible in the step itself.
- Step 9 and rollback: kept every ordering, budget and resume rule. Simplified the wording of the failure lines and merged the duplicate phrasing about writes never running on both paths.
- Rollback failure handling merged into one line that points to the abort before step 6 and the resume rule after it, instead of repeating the Postgres update in two places.
- Kept all open questions unchanged in content. Removed step-number codes that pointed elsewhere only where the step name was clearer; numbered step references remain where the order matters.
- No mechanism was added or removed. The 90 s pause, version rule, tombstone checks, lease, outbox, fence and resume rules keep their original behaviour.

### Holes
- Q6: In step 9, how do writers behave after the pause: do clients retry the 503 automatically and for how long? What do users see during the pause? (author: The files do not say whether clients retry a 503 automatically or for how long. The brief says clients already retry. The plan assumes they retry for at least the 90 s pause. During the pause, writes return 503 and are retried by clients, and reads continue. Added as the first open question.)
- Q9: What does the erasure job run on, what triggers it, and what happens to a user's data if it fails between steps (a), (b) and (c)? (author: The files only say that an erasure job exists and runs about 2,000 times a day. They do not say what triggers it, so the plan records a pending user_erasures row in the source database, and a worker retries pending rows until they are done. The failure handling is decided: step 1 (tombstone in the target, then delete the target copy) is idempotent and leaves the source unchanged if it fails. Step 2 (delete source row, outbox row and set done) is one transaction, so no partial state exists. The tombstone blocks any copy that races the erasure. Open question added for the trigger.)

## Review of mig-01 (junior-v5, author sonnet, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Rewrote the document in the skill's order: summary, terms, how it runs, rollout checklist, failure table, open questions.
- Removed the undefined sweeper lease and the backfill lease; sweepers now claim rows with FOR UPDATE SKIP LOCKED because copies are idempotent.
- Sweeper now writes the tombstone before deleting the row on the other side, in one transaction, so a concurrent stale upsert cannot resurrect an erased user.
- Defined version ownership (app bumps it, DBs store it) and added the Postgres-SoT bump rule.
- Added the reason for the dual_write_all_since barrier in Step 3 and in the terms.
- Spelled out that the abort at 40 seconds ends the 503s itself and leaves outbox rows for the sweeper.
- Fixed the Step 11/12 timing: Step 12's only gate is that Step 11 is deployed; removed the duplicated 14-day condition.
- Fixed an inconsistency: Step 11 stopped the sweeper though Step 10 kept copying erasures to MySQL until Step 12; Step 11 now keeps the sweeper and erasure copy until Step 12.
- Added an open question about erasures in the 7 days between rename and drop of users_retired.
- Added a failure table and a state table; merged the repeated rollback and abort text into one switch section.
- Step 1: create users_sync_outbox on Postgres too (and users_control starts as not_sot there), fixing the missing Postgres outbox.
- Terms (Outbox, Sweeper) and section 2: outbox exists on both databases; one sweeper deployment polls both and copies from the database holding the row to the other.
- Section 1: copy of a Postgres-assigned id is a plain insert into MySQL users; stated that MySQL users already has the same columns.
- Section 1 and failure table: a stale-version update raises StaleWrite as today, with no outbox row and no copy.
- Step 8 and state table: Postgres outbox is the one created in Step 1, drained by the same sweeper.
- Step 6: added a 'Stale reads accepted' line explaining that a failed inline copy can show old data until the sweeper catches up.
- Section 3 (Deletes): stated that the erasure transaction checks the control row, gets the 503 during a pause, and is retried by the job queue; added a row to the failure table.
- Step 10: defined what writes do in pg_only (control-row check stays, no outbox row or copy for creates and updates; erasure deletes still use the outbox). This fixes an undrainable-outbox hole.
- Step 5: defined 'both directions' and made candidates with a pending outbox row not count as mismatches.
- Open questions: added the assumption that the erasure job runs on the job queue.
- Rewrote the summary to first say how users works today (replica reads, primary writes, version bump, StaleWrite, hard-delete erasure), then the main flow and why it is cautious.
- Terms: merged Copy and second hop; folded the version-source answer into Version rule (app sets version, DBs only store it); put the reason the sweeper avoids Redis jobs in the Sweeper term; dropped the lease wording; defined migration_state, Backfill and Comparison in one line each.
- Separated how the system runs (write path, repair, deletes, switch, backfill progress, new ids, state table) from the rollout checklist, which keeps the 12 steps with trigger, change, state and failure handling.
- Removed cross-references like 'Section 6' and 'Switching the source of truth' codes; steps now point to the described mechanism in plain words.
- Merged the repeated 'outbox exists on both, only SoT receives rows' and sweeper-direction statements into the Outbox term, Sweeper section and Step 1 reason.
- Merged the stale-version, erasure-503 and abort explanations into single places in the how-it-runs section and the failure table, shortening Steps 8 and 9.
- Tightened Step 5 into a bullet list explaining the two walks, persistent mismatches and pending outbox rows.
- Kept the stale-read acceptance, pg_only behaviour, Step 12 gate reasoning and open questions; added no new mechanisms.
- Cut minor repetition, e.g. 'It needs no knowledge of which side is SoT' detail, extra reasoning lines in Steps 4 and 11, and the redundant explanations of idempotent copies.

### Holes
- None.

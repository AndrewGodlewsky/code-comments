## Review of mig-01 (junior-v4, author haiku, seeded-implicit)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a Terms section defining the source of truth, copy rule, tombstone, pending, sweep, comparer, backfill progress, migration state and the write_mode values.
- Split the checklist into phases: tables and deploy, dual writes, backfill and compare, read ramp, switch to Postgres, keep MySQL in sync, pg_only and drop, and rollback.
- Gave every step the same parts: starts, does, state, and what happens if it fails.
- Added the copy rule with the version check, the tombstone check and a per-user lock, so deletes cannot reappear and copies cannot interleave with erases.
- Made each pending row live in the source database, in the same transaction as the change, so a failed copy is recorded even after a crash.
- Specified the backfill: reads in id order in batches of 2,000, a wait while replica lag is above 5 seconds, progress saved after each batch, and a heartbeat that restarts it.
- Defined the comparer's mismatch recheck on the MySQL primary, and defined a clean pass as a full pass with zero mismatches and no pending rows.
- Specified the switch to pg_primary as a paused sequence with substeps, the Postgres sequence restart to the larger max id plus 1,000,000, and a 75-second abort back to dual.
- Specified the rollback as a paused sequence that drains Postgres pending rows into MySQL before flipping back to dual.
- Stated that the never-fail-the-request rule applies only before the switch, because Postgres is the source after it.
- Listed the unknowns (scheduler for the sweep, in-flight write time, comparison duration, email clash, flag storage) under Open questions rather than guessing.
- The file is longer than the 1.5x target. The brief's fixed requirements (repair, tombstones, id assignment, pause budget, rollback) needed the extra mechanics, and I did not cut any part that the main flow needs.
- Added a short description of how UserRepository works today, and a summary of the main flow, before the terms.
- Defined version, the pending row's contents (user id, version, erased flag), the sweep's compare-and-delete rule, job progress, heartbeat, dead-lettered, and write_mode as a string flag in app.flags.
- Step 3: the Postgres copy now runs inside the request before the response, with a short timeout, and the erase writes are spelled out for both databases.
- Step 4: backfill is started by an operator, skips ids that have a pending or tombstone row (checked on the MySQL primary), and the sweep restarts it by heartbeat, which covers dead-lettered jobs.
- Step 5: each comparer pass starts from the first id, and the job is started by an operator.
- Step 6: the known gap now says exactly what a user sees (old or missing row, no error), including their own change.
- Step 7: substep 3 corrected to check MySQL pending, since Postgres has no pending rows in dual mode; the step is run by a person.
- Step 8: the comparer's start is stated, and the failure rule is kept.
- Open questions: removed the write_mode storage question (flags are strings in app.flags), kept who changes it; added the pause-budget risk for step 7, the erase race that could reinsert a row, and whether stale reads are acceptable.
- Removed repeated wording in the steps so each step stands alone; the step order and all fixed requirements are unchanged.
- Shortened the overview to one paragraph: what changes, how the main flow goes, and the best-effort copy rule.
- Trimmed the terms to one line each and merged the flag-refresh timing note into the terms section.
- Rewrote the sweep, copy rule and pending-row definitions in plainer sentences without changing what they do.
- Gave every step the same four parts (Starts, Does, State, If it fails). Step 10 gained a State line, which was missing before.
- Split step 3 into create/update and erase sub-points, so the two paths read separately.
- Kept the known read-staleness gap inside step 6, where a reader meets the read path, instead of a separate note.
- Moved the rollback out of the ordered rollout steps into its own section with the same four parts, because it is an alternate path, not the next step.
- Merged the duplicate wording about the 75-second fallback and the 90-second pause limit into each step's If it fails line.
- Removed repeated explanations of the Postgres-first and MySQL-first copy paths that the step text already states.
- Left every open question as written, with no answers added and no mechanisms added. Plan intent is unchanged.

### Holes
- Q3: What are the values of `users.write_mode`, and where is the flag stored and changed? (author: The values are a decision: mysql, dual, paused, pg_primary and pg_only. The existing docs do not say where the flag is stored or who changes it, so I cannot answer that part. It is listed under Open questions.)

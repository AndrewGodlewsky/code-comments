## Review of mig-01 (junior-v4, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Q1: added a Version bullet stating the app increments version in UserRepository.update and there is no trigger.
- Q2: fixed the dual-write description, which said to read the row inside the same MySQL transaction after the commit. Values are now read before commit and copied after, with the synchronous cost stated.
- Q3: removed the undefined 'erasure copy' phrase. The Postgres removal is the tombstone apply under the copy lock, described in Deletes and step 5.
- Q4: deletes now apply the tombstone to Postgres right after the MySQL delete commits, with the sweeper as fallback, so an erased user is not readable until repair.
- Q5: backfill and the full comparison run in their own leader loop with a separate advisory lock, and the backfill leader decides the step 4 gate.
- Q5/Q6: added a Postgres instance_status heartbeat table written by every instance every 5 s; every gate and the 'every instance' checks in steps 4, 7, 8, 9, 10, 12 and 15 now read heartbeats instead of app_flag_value. The metric is kept for dashboards. instance_status is added to steps 1 and 3.
- Q7: the operator starts a switch command; the command runs the drain, and step 11 now states the drain's finish condition (no pending rows and matching window hashes).
- Q8: shadow writes after the switch use the same version-guarded update-or-insert rule as the reverse sweeper, so the two writers cannot overwrite newer rows.
- Q9: reads at 100% go to the Postgres primary, and read-your-writes behaviour is stated in Reads.
- Ids: shortened to one bullet. The sequence-setting rule lives only in steps 11 and 15, so it is not said twice.
- Leaders: added a bullet naming the sweeper loop and the backfill loop with their own locks, so the reader can tell which process runs each step.
- Open questions: added the failed-copy read window, the unknown read-replica question for pg-core, and the snapshot retention owner decision.
- Removed `users.mysql_shadow=true` from step 3 and defined it in step 12, where it is read and step 17 turns it off (Q10).
- Step 12 now states the post-switch update rule: the caller's read version is checked in the Postgres UPDATE, which adds 1 to version (Q11).
- Step 12 now states the post-switch delete path: the tombstone is first written in Postgres under the copy lock, then shadowed to MySQL (Q12).
- Sweeper direction is now set by `migration_state.sot`: the forward sweeper stops at step 12 and the reverse sweeper runs from then until step 17 (Q13).
- Read routing is stated in one place: `pg_read_percent` is bucketed per user, and after step 12 all reads go to Postgres (Q14).
- `in_flight` now includes the Postgres copy and tombstone apply. Clients retry on 503. An instance that sees fenced reports at once after its in-flight writes finish (Q15).
- 'How the system runs' now has a coverage paragraph: dual write, the sweeper, and backfill together cover every change (Q16).
- Step 15 lists its pause and abort points, and step 14 notes that a broken reverse sweeper blocks rollback (Q17).
- Step 16 uses one clock, `sot_switched_at`, instead of a second `pg_source_since` name.
- Merged the separate design-decisions list into terms, 'How the system runs', and the steps, and cut repeated rules, so the file stays near its first length.
- Moved the email collation check into step 1, so it runs before the schemas are created.
- Added open questions: failed-copy not-found for new users, how gates learn the instance list, how the app reads replica lag, and whether buckets nest.
- Cut the long Terms entries to one line each, and moved the gate and in_flight definitions into Terms so the steps use them without repeating them.
- Merged the fence and gate explanations, and the heartbeat and leader explanations, into single short paragraphs in How the system runs. Dropped the repeated statement that gates read heartbeat rows, since the Heartbeat term now says it.
- Replaced the 'Writes after the switch' section reference with 'as described above', so the reader does not have to look elsewhere.
- Step 5: turned the loop into three numbered parts with the same wording as before, and removed the duplicated retry explanation.
- Step 6: kept every check, batch rule and gate condition, and reworded the comparison bullets to shorter sentences. Removed the repeated 'leader' sentence, which is covered in How the system runs.
- Steps 1 to 18: each step keeps the Starts, Does, State and If it fails parts. Step 2 and step 3 wording tightened without changing any number or rule.
- Step 15: kept the abort and pause rules, and shortened the explanation of why each abort path exists.
- Step 18: kept the retention note and the drop precondition. Moved the open retention question to Open questions only once, instead of repeating it.
- Open questions: merged the two read-after-write and replica-capacity points into one line each, with no change to what is unknown. Intent, numbers, flags and the 80 s / 85 s / 90 s pause limits are unchanged.

### Holes
- None.

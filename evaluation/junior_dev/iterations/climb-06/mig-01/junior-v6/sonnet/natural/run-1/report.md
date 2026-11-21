## Review of mig-01 (junior-v6, author sonnet, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Design decisions: defined what a repair is (the inline copy did not finish) so a newcomer sees why the outbox is needed.
- Design decisions: explained users_control and the fence in plain words and named the 503 as retryable.
- Design decisions: stated that the version column already exists and who bumps it, and that overlapping copies are harmless by the version rule.
- Flags: added who sets flags and what app_flag_value is and where it is measured.
- Step 2: spelled out the order of a dual write (commit, inline copy, outbox delete, respond) and what the client sees.
- Step 3: noted that relay and inline copy applying the same row is a no-op.
- Step 5: gave the reason for reading the replica and explained how stale rows and deleted users are handled.
- Step 10: defined the watchdog and stated that the script need not confirm flag arrival because both fences are closed.
- Added an Open questions section for where the switch script and watchdog run.
- Outbox decision now says rows are written only while dual_write is on (was wrongly 'every write'), and states nothing is copied while off.
- Step 2: added which write path a request uses (cached users.writer read at request start; fence catches stale flags).
- Step 2: delete now follows the same inline-then-relay sequence, and says Postgres data stays readable briefly until the delete applies.
- Step 4: added a line that writes during the flag-skew window reach Postgres via the backfill and comparator.
- Step 6: replaced 'outbox row out of the way' with: skip ids that still have a pending outbox row and check them on a later pass.
- Step 7: added a freshness note about reads that hit Postgres before a delayed copy lands.
- Step 10: drain wait is bounded by T+45 with watchdog abort, and the state left after an abort is listed.
- Step 11: says dual_write is ignored and the MySQL-first path is unused once writer=postgres.
- Open questions: added that the exact GDPR erasure deadline is unknown.
- Removed the unused epoch column from users_control (design decisions, step 1, step 10, abort notes) because nothing reads it.
- Step 11 now spells out the Postgres-first write sequence: fence, write, read-back, pg_outbox row, commit, inline 300 ms copy to MySQL, delete the row on success, respond; the reverse relay covers failures.
- Step 11 now says how version and ids are assigned after the switch and how MySQL receives them.
- Step 11 now describes the delete path end to end, tombstone first in Postgres and then mirrored to MySQL.
- Read path (steps 2 and 11): the fallback to the MySQL replica on a miss now applies only while writer=mysql; after the switch a Postgres miss is final, which fixes a deleted user reappearing from MySQL.
- Step 10 and the design decisions now explain why the empty-outbox wait also catches an in-flight inline copy, and that Postgres opens only after the drain.
- Step 4 failure handling: re-enabling dual_write after any gap always resets backfill progress to 0, reruns the backfill and requires a fresh clean comparison.
- Reorganised into the required order: summary paragraph (how today works, main flow, why), terms, a 'How the system runs' section, rollout steps, a failure table, open questions.
- Separated runtime behaviour (MySQL-first writes, deletes, Postgres-first writes, reads, switching) from the rollout steps, so step 2, step 10 and step 11 no longer carry the mechanism text.
- Merged the Design decisions section into the terms and runtime section: fence, outbox, repair, version rule, tombstone, relay, watchdog and flags are now defined in one line each.
- Merged the repeated 'inline copy then relay' description from steps 2, 3, 10 and 11 into single write-path descriptions.
- Merged the repeated read fallback rules from steps 2, 7 and 11 into one Reads section.
- Added a short 'What happens when things fail while running' table.
- Removed cross-references such as 'see step 3 / step 12' in the mechanism text and replaced with plain descriptions.
- Added plain definitions for source of truth, dual write, outbox, repair, relay, backfill and comparator. Added a reason for reading the backfill from the replica (keep the bulk read off the primary; reporting jobs share it).
- Cut the junior's detail-only answers that the plan does not need (exact formats, library choices).
- Kept every stated number and rule: 300 ms, 10 s breaker, 200 relay batch, 2,000 batch/chunk, 5 s lag, 10 min wait, 60 s recheck, 256 stripes, 1,000,000 id gap, 1/10/50/100 stages, 3 days, 24 h comparator, T+45/T+75, 90 s, 14 days, 7 days, 5 minute alert, 10 s rollback outbox age.

### Holes
- Q8: Who or what runs the switch script and the watchdog, and how does the operator know the flag has reached all instances before step 5 of the switch? (author: Which host or job system runs the switch script and watchdog is not decided; an operator runs the script and the watchdog is a separate process. The operator does not need to confirm flag arrival before opening Postgres, because both fences are closed until then, so a stale instance can only get a 503 (decided). Clarified in step 10 and added the host to Open questions.)

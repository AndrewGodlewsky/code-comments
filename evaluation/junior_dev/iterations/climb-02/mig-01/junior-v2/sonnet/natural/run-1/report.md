## Review of mig-01 (junior-v2, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a short 'How the pieces fit' section explaining app.flags and its 30 s refresh, the version column, and the mode flag (Q1, Q2).
- Added a 'Request flow in mysql_dual' bullet walking one update: one MySQL transaction for fence read, users write and outbox row, then inline apply (Q3).
- Rewrote 'Deletes use tombstones' as numbered steps: MySQL tombstone in the source transaction, then the Postgres tombstone and delete via inline apply or worker (Q4).
- Clarified that the drain worker uses pg_copy, that inline failures are not signalled, and the retry delay of about 12 s (Q5).
- Stated that the fence a writer reads depends on its mode flag (Q6).
- Named users-sync-worker as the reverse drain after the switch, and said it stops reading pg_outbox in step 10 (Q7).
- Merged 'What the worker does' wording and removed the duplicate mode-flag values from step 2 to avoid repetition.
- Added a Create bullet: fence read, insert with MySQL-assigned id and outbox row in one transaction, then inline apply.
- Inline apply: stated that an open circuit breaker skips the Postgres call and leaves the outbox row for the worker.
- Step 8 sub-step 1: replaced 'in the same minute' with an explicit order (pause MySQL, then set the flag) and why the order is safe.
- Step 8 Pause length: rewritten so each instance resumes on its own flag refresh, old-flag instances keep getting 503 safely, and the pause is the longer of 30 s and the drain time.
- Step 8 From now on: defined the MySQL tombstone check (FOR SHARE gap lock) and said the pattern is mysql_dual with the databases swapped.
- Step 4 Batch handling: added one sentence on why a stale replica row cannot overwrite newer data.
- Step 6: removed the 'miss while below 100%' special case. A miss or error always falls back to the replica, so the rule is simpler and safer.
- Merged the repeated Create/Update/Delete flow descriptions into one 'Write flow in mysql_dual' list covering all three.
- Folded the 'Inline apply', 'What the worker does' and 'After the switch' bullets into the Drain worker bullet and step 8, removing the duplicated reverse-drain description.
- Removed the separate 'Pausing' and 'Copy paths skip the fence' sub-bullets by merging them into three fence bullets.
- Merged 'Why above the counter', 'Why the gap' and Rollback sub-bullets of the id sequence into one bullet; the rollback counter check lives only in step 9.
- Dropped the 'Version' and 'Flags' restatements to one line each and trimmed repeated explanations of the 30 s flag lag.
- Shortened step 4 by merging batch handling and failure cases; moved the stale-replica rationale into one line.
- Cut redundant phrasing such as 'Record the go decision' detail, 'Drop them to undo', and the step 9 'Changes: nothing' elaboration.
- Added a short Open questions section at the end for the judgment-call values (hold times, 1M margin, 250 ms timeout).
- Removed the claim 'Repair is automatic via the worker' as a separate State line in step 3 by merging it into Changes.

### Holes
- None.

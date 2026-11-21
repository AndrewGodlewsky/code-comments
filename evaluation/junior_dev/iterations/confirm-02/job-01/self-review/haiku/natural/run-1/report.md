## Review of job-01 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Fixed the cardinality from JOB_RUNS to RUN_ATTEMPTS to zero or more (||--o{). The original said one or more, but pending, skipped and cancelled runs have no attempts.
- Stated that job_schedules needs UNIQUE (id, tenant_id) for the composite foreign key on job_runs, and wrote out what that key enforces. The original named the key without saying what it required.
- Added a 'What the statuses mean' section that defines each run status and each attempt outcome, and explains why pending includes runs waiting for a retry.
- Explained the single-run guarantee: the schedule row lock prevents two workers from racing, and the unique constraints are a backstop.
- Defined the terms used without explanation: SKIP LOCKED, ON CONFLICT, partial unique index, tick, reaper, presumed dead, fencing token, and backoff.
- Clarified that the enabled and not-paused checks are part of the claim statement, so a run cannot start after a disable or pause commits.
- Explained what a worker does when a heartbeat update matches zero rows.
- Made the composite-key, DST, retention, and partition notes plain, and kept the same headings, diagram, index list and three decisions to confirm.
- Stated in the decisions that the 15-second tick is a choice, not a requirement, and kept the two interpretations (backoff timing and cancelling runs waiting for retry) marked as items to confirm.
- Added a short overview at the top that says what the system does, how many workers run, and the three jobs each worker does on every tick.
- Added a Key terms section that defines schedule, fire time, run, attempt, heartbeat, presumed dead, row lock, unique and partial unique constraints, fencing token, cron, and IANA timezone.
- In the status section, spelled out what each run status and attempt outcome means in plain words, and stated that a running run always has at least one attempt.
- In How the schema meets the requirements, changed the active-run wording to say that finished rows are outside the partial index, and explained why workers lock the schedule row.
- Split the Claiming steps into a numbered list and explained that the enabled and not-paused checks are part of the claim statement.
- Showed the heartbeat and cleanup SQL in code blocks, and explained the fencing check as a single rule.
- Renamed the reaper and explained what it does on each tick, including that the dead attempt counts as one of the 3 attempts.
- Clarified the backoff note and the DST note, and added a sentence that the index for the due-schedule query is the partial index on next_fire_at.
- Kept the Mermaid erDiagram unchanged, so the table and relationship definitions are the same as before.
- Kept the Decisions to confirm section and its three items unchanged in substance.
- Added a plain-language opening that explains what tenants, schedules, workers and the database's role are, plus a one-line summary of rows (schedule, run, attempt).
- Expanded the Key terms list with definitions a reader without project context needs: transaction, idempotent, backoff, reaper, claimable, UTC, DST, row lock, and a worked cron example (`0 9 * * 1`).
- Added a 'Life of a run' section that walks through the status flow in five steps, so the status and attempt sections read as one lifecycle.
- Fixed the cleanup SQL: Postgres's plain DELETE does not accept LIMIT, so the batch now selects up to 1000 IDs in a subquery and deletes those rows.
- Clarified wording in the requirements mapping, clocks bullet, claim and heartbeat sections (for example, 'the reaper has already taken it over', and why a late write matches zero rows), and the run-creation intro, without changing any technical behaviour.
- Made the 'skipped' and 'cancelled' status definitions and the 'attempts are optional' rule explicit with the reason they can have zero attempts.
- Kept the Mermaid diagram, the statuses, the schema and index design, the retry and fencing rules, and the three decisions to confirm unchanged in substance.

### Holes
- None.

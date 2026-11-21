## Review of job-01 (junior, author sonnet, natural)

Rounds: 5. Ended: teachback-correct.

### What changed
- Claim ORDER BY changed to COALESCE(next_attempt_at, created_at) so due retries are not starved by newer queued runs.
- Run creation step 4: stated that next_fire_at always advances, including when the insert hits ON CONFLICT.
- Claiming: stated that the attempt insert is in the same transaction so a mid-claim crash rolls back; added a line that a worker claims repeatedly up to a concurrency limit and runs handlers concurrently.
- Heartbeats: stated that the 100s self-lost rule is shorter than the 2 minute reaper threshold, and that a stale worker discards its result when its fenced write matches 0 rows.
- Retries: added that the worker enforces a per-job-type timeout and that an unregistered job_type is an ordinary failed attempt.
- Constraints: added a Handlers line (the app registry maps job_type to a handler) and a note that the cron validation also rejects schedules with no fire time in the window.
- Reaper step 1: noted that a running run always has an open attempt row.
- Added an Open questions section for the handler timeout duration and the concurrency limit.
- Run creation step 3: replaced 'a queued insert that conflicts on the partial index is retried as skipped' with the reason the active-run check is reliable under the schedule row lock, and said the partial index is only a safety net that rolls the transaction back.
- Retries: stated what a handler timeout does (signal stop, record failure at once through the fenced transaction, stop heartbeating) and that an ignoring handler may overlap with the retry, accepted because handlers are idempotent.
- Claiming: stated that a retry inserts a new attempt row and that the previous attempt is already closed (Q11).
- Pausing and disabling: resume and enable now first cancel leftover queued runs, closing a race where a pause leaves a stuck queued run that would make later fire times skipped (Q12).
- Fenced writes: every exit from running now clears worker_id and heartbeat_at, and success sets status and finished_at explicitly (Q13).
- Tick loop and fenced writes: added DB-outage behaviour, with the tick retried next time and the outcome write retried (Q14).
- Run creation step 2: clarified that fire_time is the latest fire time at or before now(), equal to next_fire_at unless several were missed (Q15).
- Run creation step 1: stated that surplus due schedules wait for the next tick, oldest first, so no tenant is starved (Q16).
- Reaper: replaced one SELECT FOR UPDATE followed by separate transactions with a plain candidate read, then a per-run transaction that re-locks and re-checks the row, so the run cannot change between check and transition (fixes a real hole found by Q21).
- Fire time computation: stated that a cron library is used, with DST rules (nonexistent local time fires just after the gap, repeated time fires once), and added this to open questions as my own choice.
- Schedule creation: added a line that next_fire_at is set in the same INSERT that fires the 50-cap trigger.
- Claiming: noted that the retry_wait branch deliberately skips the enabled and paused check.
- Clock: clarified that the handler timeout is a local duration timer and not a stored timestamp, and repeated this in the retries section.
- Cleanup: stated that each worker uses a local 24-hour timer with no record of earlier runs, that the advisory lock only prevents overlap, and that only finished runs are deleted; updated the tick description to match.
- Section 1 step 3: added that a queued run waits for worker capacity and a fire time arriving meanwhile is recorded as skipped (Q23).
- Section 2: added that a soft-deleted schedule's row still exists, so a retry_wait retry still runs (Q24).
- Section 3: spelled out the 100-second self-lost rule as a local timer reset at each successful heartbeat, with the worker stopping the handler and writing nothing; stated the order of the two fenced statements (Q26, Q25).
- Section 4: stated that failure uses the same two fenced statements in the same order as success, that the DB computes now() + interval, and that the claim query finds the run once it is due (Q25).
- Section 5: stated that the reaper's row lock replaces the token fence, and that its failure transition clears worker_id and heartbeat_at and sets finished_at only when the run becomes failed (Q27).
- Section 6: made resume one app transaction that cancels queued runs, clears jobs_paused_at and recomputes next_fire_at per enabled schedule; added that a retrying run keeps retrying after its schedule is soft-deleted (Q28, Q24).
- Reordered to the skill layout: summary (with how the existing system looks today), terms, diagram plus constraint notes, shared rules, numbered steps, failure table, guarantees, open questions.
- Added a Terms section defining fencing token, heartbeat, presumed dead, active run, skipped run, reaper, handler, SKIP LOCKED, partial index, worker, attempt, fire time.
- Merged the per-question patches into the steps they belong to: each of sections 1-7 now states trigger, action and a Failure note; the DB-outage, retry-write and rollback lines moved into the loop intro and section 3.
- Moved the repeated 'clear worker_id and heartbeat_at' explanation into one shared rule (Leaving running) and shortened the Clock rule to cover the local duration timers once.
- Added a single failure table collecting failure handling in one place.
- Merged duplicate statements: the DB-computed retry delay, the claim ordering rationale, the fenced-write order and the reaper re-check each appear once; the retry section now points to section 3 for the shared SQL.
- Cut the repeated 'a tenant has at most 50 schedules' reasoning in the scan and the repeated Race with claim restatement of the retry rationale; trimmed pause/resume prose to a lead sentence plus bullets.
- Added pending-retries pause assumption to Open questions so it is not buried in section 6 only.
- Fixed the cleanup lock text that had HTML entities (&lt; &gt;) back to <job-cleanup key>.
- Updated the one-active-run guarantee row to name the active-run check under the schedule lock as the primary mechanism, matching section 1 step 3.
- Checked against first version: all numbers (50, 5 min, 3-10 workers, 30 s, 2 min, 3 attempts, 1/5 min, 90 days, 12-month window, LIMIT 1000, 100 s) and all constraints and indexes are retained; nothing from the original was dropped.

### Holes
- Q2: What is the handler timeout, and what enforces it? The doc says 'throws or times out' but gives no duration. (author: The brief gives no handler timeout. I assumed the worker enforces a per-job-type timeout and treats expiry as a thrown error. The duration is added under Open questions.)

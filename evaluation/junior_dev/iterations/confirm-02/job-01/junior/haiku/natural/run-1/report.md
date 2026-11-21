## Review of job-01 (junior, author haiku, natural)

Rounds: 5. Ended: teachback-correct.

### What changed
- Added a summary and a terms list that defines worker, cron expression, IANA timezone, fire time, run, attempt, claim, heartbeat, presumed dead, fencing token, SKIP LOCKED, partial unique index, soft delete and idempotent (Q1, Q2, Q4).
- Moved constraints from %% notes into the diagram's attribute comments, and removed the duplicate constraint paragraph.
- Added a saving step (step 1) that sets the first next_fire_at on create, cron or timezone edit, enable and tenant resume, and placed the 50-schedule cap and 5-minute gap check there (Q3).
- Stated that editing the cron leaves queued runs in place, because the brief cancels unstarted runs only on disable or pause (Q3).
- Added the handler lookup by job_type and the payload hand-off to the claiming step (Q2).
- Stated that each worker runs three timers: 30 seconds for creation, 5 seconds for claiming, and a 30-second heartbeat. Stated the 30-second sweep (Q4, Q5).
- Stated that the heartbeat runs on its own timer, and what a worker does when it loses its run (Q5, Q6).
- Made the creation transaction's failure behavior explicit: rollback leaves next_fire_at unchanged, so the next tick retries (added during the rewrite).
- Stated that skipped and failed runs trigger no notification, and that history shows them (Q7).
- Added soft delete to the disable and pause step, so that a delete also disables the schedule and cancels queued runs (Q8).
- Tenant resume now sets next_fire_at for every enabled schedule of the tenant, which the first version did not say.
- Made the 50-schedule cap count live (not soft-deleted) schedules, which the first version did not say.
- Merged the retry wait rule into step 5 so that crash recovery refers to it rather than repeating the values (cut repetition).
- Added a failure table covering each failure case the questions raised.
- Added open questions for maximum run time, notifications and poll rates, since the brief does not decide them.
- Summary: cut to one short paragraph; removed the repeated mechanism list and added the one-line note on how the system stands today (tenants table only, no job code).
- Terms: kept each definition to one line; clarified Claim as 'a queued run that is due'.
- Step 1: resume now clears jobs_paused_at and resets next_fire_at in the same transaction; enabling and resuming are stated as not catching up and not reviving cancelled runs.
- Step 2: F explained as possibly well after next_fire_at following an outage; stated that the skipped row does not clash with the partial unique index; stated that a locked schedule is skipped by other workers.
- Step 3: a new run and a retry are described as the same kind of row picked by the same statement; attempt_no is the new attempt_count; the claim sets heartbeat_at so an early crash is still detected; a late queued run still runs.
- Step 4: the heartbeat timer's start and stop are stated; a database error on the heartbeat is separated from the zero-rows case and handled by a retry at the next tick, with no new stop rule.
- Step 5: added ended_at on failed attempts so every attempt shows an end time, as the brief requires.
- Step 6: the guard uses the attempt count the sweep read; wording about the wait counting from detection kept and moved to open questions.
- Step 7: a queued run waiting to retry is cancelled like any queued run; its attempt history and final_error (empty) are stated.
- Failure table: added rows for a worker dying right after claiming, a heartbeat that cannot reach the database, and an outcome transaction that fails; the 'no handler' and 'dies during run' rows kept.
- Open questions: added the handler-on-a-worker-without-database question and the retry-wait start question; kept maximum run time, notifications and poll rates.
- Step 3 trigger and How it runs: the claim timer now acts only while the worker is idle, and a worker runs one handler at a time (Q16). The Idle worker term was added to Terms.
- Step 3 Late runs: corrected the pickup delay. Runs are created on the 30-second tick, so a run can appear up to 30 seconds after its fire time, then wait up to 5 more seconds for a claim. The earlier 'within about 5 seconds' statement was wrong.
- Step 3: added a Bursts note with the N / W ticks rule and a worked example (Q17).
- Failure table: added a row for many runs due at once.
- Open questions, Poll rates: noted that a shorter claim poll would shorten bursts.
- Step 5: a retry goes back to queued only if the schedule is still enabled and not deleted and the tenant is not paused. Otherwise the run is cancelled, with an empty final_error. This keeps the brief's rule that runs not yet started are cancelled (Q21).
- Step 2: stated that a run waiting to retry counts as queued, so a new fire time becomes a skipped row. Also stated that next_fire_at moves past F, so the schedule is not due again without a new occurrence (Q18, Q19).
- How it runs and Terms: added that every time check uses the Postgres now() clock, and defined the database clock term (Q20).
- Terms and step 3: defined the worker id, how it is made, and when a worker is idle or busy. Step 4: the worker stays busy until the handler returns, even after a stop request (Q22).
- Step 6: the retry rule from step 5, including its flag check, applies to presumed-dead runs. Step 7: a running run that fails with retries left during a pause is cancelled, not requeued. Failure table: added the row for this case.
- Open questions: added the case of a handler that ignores the stop request and keeps its worker busy (Q22).
- Cut nothing from the first version. Added only the lines above. Kept the diagram and all brief requirements.
- Step 2: a paused tenant's schedules are not selected, so next_fire_at stays old until resume. The creator does not check the 50-schedule limit, which is checked only on save.
- Step 3: two workers cannot claim the same run because SKIP LOCKED and the status change in the same statement. An idle worker with no due run waits for the next tick.
- Step 3: the handler is called with the payload only, and the fleet's one-handler-per-worker limit has a noted exception for the overlap in step 4.
- Step 4: added the overlap case. A stalled worker's handler may still run when the next attempt starts. The fence stops database writes, not side effects, and handlers are idempotent.
- Step 5: the run keeps its row and fire_time when it goes back to queued.
- Step 6: the sweep's guarded write now also requires heartbeat_at to be stale, so a live worker's just-landed heartbeat is not taken over. Added the rule that the first commit wins a race between a worker write and the sweep.
- Failure table: added a row for a clean worker shutdown during a deploy. It stops claiming, keeps the heartbeat until the handler returns, then exits. A kill falls back to crash recovery.
- Added a plain definition for each name a newcomer would not know: tenant, schedule, job type, payload, handler, registry, worker id, idle worker, guarded write, stop request, row lock, ON CONFLICT DO NOTHING, tick. Defined the database clock once, in the terms only.
- Gave every step the same four labels (Trigger, What it does, Data kept, On failure). Added the missing On failure lines to step 7 (whole transaction rolls back) and step 8 (rows already deleted stay deleted; next daily run picks up the rest). Added a short On failure line to step 6 (a failed sweep leaves the run running for the next sweep) and to step 4.
- Merged the duplicate-work notes into step 2 and moved the creation-tick explanation of ON CONFLICT there, once. Shortened the How it runs intro so it no longer repeats the database clock rule.
- Stated in step 3 that the worker is busy from a successful claim, and in step 4 that the stop request does not free the worker. These were already in the first version; they are now in the step where they apply.
- Added a Build notes section (new nullable TENANTS.jobs_paused_at, no backfill needed, other three tables are new), kept separate from how the system runs.
- Kept every stated fact from the brief and the prior document: 3 to 10 workers, no leader, Postgres only, 50-schedule cap, 5-minute minimum gap, one run per fire time, skip while in progress, drop older missed fire times, 30 s heartbeat, 2 min presumed dead, 3 attempts with 1 and 5 minute waits, fencing, cancel on disable or pause, no catch-up on re-enable or resume, history fields, 90-day cleanup, idempotent handlers. The Mermaid erDiagram is unchanged.
- No behavior was changed. The only text corrections are wording: the failure table rows now say stop request and guarded write, and the sweep guard is described once, with its heartbeat condition explained in the step where it applies.

### Holes
- None.

## Review of job-01 (junior, author haiku, seeded-implicit)

Rounds: 1. Ended: teachback-correct.

### What changed
- Added a summary that says how the current system works (tenants table only) and how the main flow runs.
- Added a terms section defining schedule, fire time, run, attempt, handler, lease, heartbeat, fence, reaper, SKIP LOCKED and in progress.
- Added the full status list (queued, running, retry_wait, succeeded, failed, skipped, cancelled) and the transitions between them.
- Added attempt_count as the fence, and the rule that every worker write must still match lease_owner and attempt_count.
- Added the unique key on (schedule_id, scheduled_for) and a partial unique index so only one run per schedule is in progress.
- Added available_at for backoff, attempt_no, started_at and ended_at on RUN_ATTEMPT, and the outcome values.
- Added the tenant status values and the schedule rule that stops disabled schedules from running.
- Replaced the vague retry note with the exact backoff (1 minute before attempt 2, 5 minutes before attempt 3) and the 3-attempt limit.
- Explained the reaper: it runs on every worker's poll, finds runs with no heartbeat for 2 minutes, and counts the dead attempt.
- Explained overlapping (skipped run) and missed (latest fire only, older dropped) using the brief's rules.
- Explained pause, disable and re-enable: queued and retry_wait runs are cancelled, running runs finish, and no catch-up happens.
- Added the history cleanup rule: finished runs older than 90 days are deleted with their attempts, and runs in progress are never deleted.
- Added the limits (50 schedules per tenant, 5-minute minimum interval) and a failure table covering each case.
- Moved the open questions to the end: lease-loss handler stop, poll and cleanup frequency, and where the limits are enforced.
- Summary cut from four sentences to three. It now says what the system is, how the workers coordinate, and why the fence is needed.
- Added one-line definitions for cron expression, timezone, handler idempotence, SKIP LOCKED, partial unique index, reaper and in progress, in answer to the junior's questions about those terms. Fence and lease definitions now say what the value is compared against.
- Merged the limits (50 schedules, 5-minute minimum, checked on save) into one Limits section. The first version stated them only in the open questions and the failure table.
- Added the two overlap and missed-fire-time rules once, as rules that apply to every step, instead of repeating them in several steps.
- Added the tenant-facing run history requirement from the brief, which the first version left out.
- Rewrote each step as trigger, action, and where its data lives, in plain short sentences. Removed the per-step failure notes and kept all failure handling in one table, so each fact appears once.
- Answered the junior's question about the reaper by stating that the dead attempt counts toward the 3 because attempt_count rises at claim.
- Added a failure row for a failed history cleanup (nothing deleted, retried next run). This is a simple handling decision made because the brief does not specify one. It is not a new mechanism.
- Stated that a pause or disable happens in one transaction with the cancellation, which the first version implied.
- Kept the diagram unchanged, the three open questions, and every requirement and limit from the brief.

### Holes
- None.

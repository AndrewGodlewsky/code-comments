## Review of job-01 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Added a Terms section defining fire time, run, attempt and lease, since a reader unfamiliar with the project would not know these words.
- Added the missing constraints to the diagram: the unique key on (schedule_id, scheduled_for) that enforces one run per fire time, and the unique key on (run_id, attempt_no). Also noted the 50-schedule and 5-minute limits.
- Added columns the workflow needs but the diagram lacked: available_at on JOB_RUN (for retry waits and pending timing), and started_at, ended_at and attempt_no on RUN_ATTEMPT (the history requires start and end times).
- Listed the allowed status values for runs and attempts, and explained what each status means.
- Rewrote the one-line notes as sections on run creation, claiming, heartbeats, retries, crash recovery, overlaps and missed fire times, pausing and resuming, and history cleanup. Each section now explains the steps and how it meets the spec.
- Explained how attempt_count and lease_owner act as a fence, so a worker presumed dead cannot overwrite the outcome of the worker that took over.
- Made crash recovery use a single path: the reaper alone turns expired runs back into pending or failed, and claiming only picks up pending runs. This removes the double-counting risk of two paths handling the same dead worker.
- Explained that disabling or pausing cancels only pending runs, and that resuming recalculates the next fire time instead of catching up.
- Added a short index note for the claim and reaper queries. Kept the Mermaid erDiagram format and the notes format.
- Added a short opening paragraph that names the three stages (creating runs, claiming and executing, recording outcomes) plus crash recovery, so the reader has the whole picture before the details.
- Defined heartbeat, reaper and fence in the Terms section, and explained schedule and cron timezone in plain words.
- Explained the Postgres clauses in plain language: FOR UPDATE SKIP LOCKED, ON CONFLICT DO NOTHING, the partial index, and the cascade delete.
- Stated that the TENANT table already exists and the other three tables are new.
- Added the cascade delete to the key constraints, since the diagram does not show it.
- Made explicit that a run waiting for a retry counts as pending, so a fire time during that wait is skipped. This is my reading of the brief's 'still in progress' rule; please confirm it.
- Stated that creation steps 2 to 5 share one transaction with the lock, so the new run and the moved next_fire_at commit together. This is an inference from the original's 'short transactions' wording; please confirm.
- Stated that the reaper's update checks in the same statement that the lease is still expired, so a worker renewing just in time is not reaped. This is an inference; please confirm.
- Explained that the fence also relies on attempt_count, and recommended a unique worker ID per process start.
- Specified that the 90-day cleanup measures scheduled_for and only deletes runs that are not pending or running. The brief does not name the timestamp, so please confirm this choice.
- Clarified that the lease is the claim and the heartbeat is its renewal, and that a worker which loses its run stops working on it.
- Kept the Mermaid diagram, headings and overall format unchanged.
- Added a short opening that says what the system is and that workers coordinate only through Postgres rows, with no worker in charge.
- Expanded the Terms section so a reader unfamiliar with cron or the database can follow it: gave a cron example, explained the timezone point, and clarified what a fence check compares.
- Added a Database terms list defining transaction, unique constraint, FOR UPDATE SKIP LOCKED, ON CONFLICT DO NOTHING, cascade delete, and partial index.
- Kept the Mermaid erDiagram and key constraints unchanged in substance.
- Made the creation steps clearer: stated that all steps for one schedule run in one transaction, said a skipped run has no attempts, and clarified that next_fire_at is the first fire time after now.
- Explained that a claim is one atomic statement.
- Replaced the retry wait wording with explicit waits: 1 minute before attempt 2 and 5 minutes before attempt 3.
- Explained why the reaper's update re-checks expiry (so two reapers cannot both act on one run) and why the fence includes attempt_count.
- Clarified that the pending-only cancel covers both new runs and runs waiting for a retry, and that skipped runs are never executed.
- Clarified the cleanup rule's status condition as 'neither pending nor running' and noted the batch deletes.

### Holes
- None.

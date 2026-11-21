## Review of job-01 (rewrite, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered: summary, terms, Mermaid diagram, then constraints, numbered steps, failure table, rollout, open questions. The summary now says how the existing app looks today.
- Added a terms section: fire time, run, attempt, worker id, in progress, lease, heartbeat, fencing check, SKIP LOCKED, reaper, now().
- Expanded the eight one-line notes into nine numbered steps. Each has a trigger, what it does, where data lives, and what happens on failure: save schedule, create runs, claim, execute and heartbeat, finish, reap, disable or pause or resume, cleanup, history read.
- Added the mechanisms the brief needs: UNIQUE(schedule_id, scheduled_for) for one run per fire time, a partial unique index for one run in progress, and the attempt number as the fencing check. A tenant-row lock for the 50-schedule limit, a 7-day gap check for the 5-minute minimum, and a share lock on the tenant row in the poller to close the pause race.
- Defined skipped runs, the latest-missed-only rule, backoff (1 minute then 5), presumed-dead counting as a used attempt, and the cancelled rule for retries when a schedule is disabled or the tenant paused.
- Added the resume and re-enable rule: recompute next_fire_at to the next fire after now, so the poller does not catch up on missed fire times.
- Diagram: dropped lease_owner, since the attempt row holds the worker id and the attempt number is the fence. Added not_before, finished_at, attempt_no, started_at, ended_at, and a status-values comment. Added check-style comments for tenant status and enums.
- Merged the 'overlapping and missed runs handled per the spec' note into steps 2 and 3 as concrete rules. It had no content of its own.
- Added a failure table, a short rollout section kept apart from how the system runs, and open questions: no max run time, schedule deletion, DST behavior, poll interval.
- Left out of the document: exact SQL, library choice for cron parsing, handler timeout design, and poll jitter. None is needed for the main flow.

### Holes
- None.

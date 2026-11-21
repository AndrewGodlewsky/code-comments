## Scheduled jobs per tenant

We're adding scheduled jobs to the SaaS app. Tenants (our customer accounts) define recurring jobs, such as "send the weekly digest", and we run them on their schedule.

**Fixed requirements**
- A schedule belongs to one tenant. It names a job type, carries a JSON payload, and has a standard 5-field cron expression plus an IANA timezone. Fire times are computed in that timezone. A tenant can have at most 50 schedules. The shortest allowed interval is 5 minutes.
- We run 3 to 10 identical worker processes. There is no leader and no separate scheduler process. The only shared infrastructure is our Postgres database. No Redis, no message broker.
- Each fire time of a schedule must produce at most one run, however many workers notice it.
- Only one run of a given schedule may be in progress at a time. If a fire time arrives while the previous run is still in progress, the new one is not executed. It shows in history as skipped.
- If no worker was up through several fire times, then on recovery only the most recent missed fire time runs. Older missed fire times are dropped and need no history entry.
- A running job sends a heartbeat every 30 seconds. If a run has had no heartbeat for 2 minutes, its worker is presumed dead and another worker may retry it.
- A run gets at most 3 attempts in total, and a presumed-dead worker counts as a used attempt. Wait 1 minute before the second attempt and 5 minutes before the third. After the third failure the run is marked failed.
- A worker that lost its run because it was presumed dead must not be able to overwrite the outcome recorded by the worker that took over.
- Disabling a schedule, or pausing a whole tenant, stops new runs. Runs already executing finish normally. Runs not yet started are cancelled. Re-enabling a schedule or resuming a tenant does not catch up fire times missed meanwhile.
- Tenants can see run history: every run with its fire time and final status, and each attempt with the worker that ran it, its start and end times, and the error if there was one. History is kept for 90 days.
- Job handlers are idempotent, so a retry that repeats partial work is acceptable.

**Existing system:** a Postgres-backed app that already has a tenants table. Nothing for jobs exists yet.

**Deliverable:** a Mermaid `erDiagram` of the tables you'd add (key columns, constraints and relationships), plus short notes on how it works: run creation, claiming, heartbeats, retries, crash recovery, pausing and history cleanup.

## Review of mr-01 (rewrite, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a short opening summary, plus a description of how the system works today (12 instances in A, 2 warm in B, replica, jobs table, Redis, DNS), taken from the brief.
- Added a Terms section: probe, replay lag, control store, fence, failover command. The control store was named in the first version but never defined.
- Defined the fence concretely. The command sets active = B and A's apps hold a short lease they renew from the control store. A stops writing when the lease lapses, so fencing works with no contact with A. This is a new mechanism I decided on, because the first version only said 'the apps respect it'. The lease length is left as an open question.
- Moved the lag check ahead of fencing, which changes the order of the first diagram. Reason: a lag stop then leaves A untouched.
- Stated that the active-region record, the lock, the run log and the fence all live in the control store, outside both regions.
- Replaced the vague 'fix up jobs' with a rule: rows left running in A are set to pending, and jobs must be idempotent. Said that jobs lost inside the RPO window are lost.
- Restored every brief fact the first version dropped: probe interval, locations and 2-of-3, 3-failures rule, no auto-failover, RPO and RTO with clock start, 30 s lag limit and override, B's workers after a writable DB, DNS after health check, 60 s TTL, session loss accepted, no auto failback.
- Added the trigger for each step, and a numbered flow that adds only what the diagram cannot show.
- Added a failure table covering crash and resume, abort before and after promotion, failed promotion, failed health check and control store outage. The first version had only 'can be resumed or aborted'.
- Made the diagram branch show the lag check outcomes (pass, stop, override) and moved the notes into the steps and rules instead of a second list.
- Added open questions: lease length, control store hosting, and scale-up time against the RTO.
- Merged the first version's loose notes (lag check, fencing, idempotent jobs, logging, sessions, failback) into the steps, so each fact appears once.
- Length is well over 1.5x the first version, which was only a 12-node diagram and 6 notes. I kept it because the brief's fixed requirements need to be stated.

### Holes
- None.

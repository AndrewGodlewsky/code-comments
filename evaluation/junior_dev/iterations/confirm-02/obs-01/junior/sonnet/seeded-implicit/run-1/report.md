## Review of obs-01 (junior, author sonnet, seeded-implicit)

Rounds: 2. Ended: teachback-correct.

### What changed
- Breach defined in the notes (above 2%, 500 requests, 3 consecutive evaluations).
- Diagram now shows the per-minute claim in Postgres, dedup on insert, first timer queued, schedule lookup at each level, ack stored, and resolve with notice to everyone in page_log.
- Added how two evaluators coordinate: both run, a unique (service, rule, minute) row lets one win.
- Added the incident row fields and the purpose of page_log.
- Added timer behaviour: queued at open, never cancelled, state checked when fired.
- Added the lookup failure and nobody-on-call handling, and the fallback trigger (incident manager on push error).
- Added that the EM is the last level with no repeat.
- Added how clear is decided and the 1%-2% case.
- Added one open question on late acks.
- Fixed the first timer: the opening step now queues escalate(level 2) and level 1 is paged directly, because the timer carries the level to page.
- Defined the order at open (id, timer, insert, page level 1) and the recovery when the incident manager dies partway.
- Made the claim and streak update one transaction, and made evaluators resend breach and clear each qualifying minute, so crashes and failed calls self-heal.
- Stated that the escalate handler sets current level, queues the next timer, and that level 3 queues nothing.
- Stated ack handling: applies only while open, duplicates and post-resolution acks ignored; added an open question about the provider echoing a reference.
- Resolved notice goes only to people successfully reached; a failed notice is not retried.
- Added definitions of evaluator, streak, timer queue, levels, schedule service and provider; reorganised into summary, terms, diagram, then run notes and data.
- Merged the long 'How it runs' bullet list into seven numbered steps in time order (evaluate, open, duplicate breach, escalate, page, ack, resolve), each with its trigger, action, data and failure handling.
- Moved evaluator crash, send-failure and incident-manager crash handling into the steps they belong to instead of separate bullets.
- Merged the separate Paging and Schedule-lookup-failure bullets: paging became its own step 5, lookup failure sits in the escalate step.
- Added a Rule term and described the metrics store in the Evaluator term, since the junior asked what these were.
- Added one line to step 2: it first checks for an existing unresolved incident, so duplicate breaches do not queue stray timers; the insert race is still guarded by the unique key.
- Rewrote the opening summary to start with how things work today (cron email) and kept it to a few sentences.
- Kept all fixed numbers and rules (60s, 5-minute window, 2%, 500 requests, 3 consecutive, 1% for 10 minutes, 5-minute escalation, push then SMS, two evaluators, one unresolved incident per service and rule), the diagram, data list and both open questions unchanged.
- Cut the repeated explanations of the claim-and-streak mechanism and of the 'safe to repeat' property so each appears once.

### Holes
- Q15: How does the ack webhook say which incident and which person acked? What if the ack arrives twice, or after the incident is already resolved (the open question)? (author: Plan assumes the provider echoes an incident id and person we send with each page; whether it supports this is not verified, so it is under open questions. A repeated ack is ignored because the update applies only while the incident is open. An ack after resolution is ignored, which is a decision and not confirmed by the team.)

## Page on-call when the public API's error rate spikes

Today a cron script emails a shared inbox when the API returns too many errors. Nobody reads that inbox at 3 a.m. We need proper paging.

**What already exists**
- The API gateway writes per-minute request counts and 5xx counts, per service, to our metrics store. The store is a time-series database you can query by time range.
- The on-call schedule service answers "who is primary / secondary / engineering manager for service X right now?". Rotations hand over at 09:00 every day, so the answer can change in the middle of an incident.
- We use an external paging provider with two send APIs: a push notification to its mobile app, and SMS. Its app has an Acknowledge button. When someone taps it, the provider calls a webhook that we register.

**Fixed rules**
- Evaluate every 60 seconds. The error rate is 5xx / requests over the trailing 5 minutes. An evaluation counts as breaching only if the rate is above 2% **and** the window holds at least 500 requests. Open an incident after 3 consecutive breaching evaluations.
- Allow at most one unresolved incident per (service, alert rule). If more breaches happen while one is unresolved, record them on it. They must not page anyone.
- An incident resolves automatically once the rate has stayed below 1% for 10 consecutive minutes. A breach after that is a new incident.
- Escalation: page the primary first. If nobody acknowledges within 5 minutes, page the secondary. If there is still no acknowledgement 5 minutes later, page the engineering manager, who is the last level. Any acknowledgement stops escalation.
- Every page goes by push first. If the push call fails, send it by SMS instead. A failed page must never stop or delay the escalation clock.
- When an incident resolves, everyone who was paged for it gets a "resolved" notice. If it resolves before anyone acknowledged, escalation stops there.
- The evaluator runs as two instances on the same schedule, for availability. Together they must not create two incidents or send double pages.

You decide where state lives, how the 5-minute timers work and how the two evaluator instances coordinate.

**Deliverable**
A Mermaid `sequenceDiagram` that covers detection, opening an incident, duplicate suppression, escalation, acknowledgement and resolution. Add short notes before or after it that cover where state is kept and how failures are handled.

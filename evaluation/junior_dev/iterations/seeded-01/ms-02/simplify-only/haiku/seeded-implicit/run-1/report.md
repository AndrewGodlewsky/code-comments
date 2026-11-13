## Review of ms-02 (simplify-only, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Cut the original Notes section. Its points now sit in the flow, the failure table and the step text: retries, dedupe on id, rollback as a flag flip, and what to watch during each move.
- Added a Summary and a Terms section. Each term (route, relay, broker, service, idempotency key) is defined in one line.
- Replaced the eight-line step list with eight rollout steps. Each step now gives what starts it, what changes, where its data lives, and what happens if it goes wrong.
- Separated how the system runs (flow and failure table) from how it ships (rollout steps).
- Replaced the bare 'dedupe on notification id' with two mechanisms: the service saves each id in `deliveries` and ignores repeats, and MailRelay's idempotency key blocks repeated sends. No lock, lease or takeover rule was added.
- Fixed a gap: the old worker now filters on `route = 'monolith'`, and this ships with the column. Without that filter, both sides would send service rows.
- Moved the retry policy into the service sender loop, on the same schedule as the old worker, instead of the plan's bare 'same policy as today'.
- Added open questions for three things the plan does not answer: MailRelay behaviour for an in-flight duplicate, how service status reaches the monolith table, and who measures the latency gate.
- Length grew from about 150 words to about 900, above the 1.5x guidance. The layout the skill asks for needs terms, a failure table and four parts per step, which the original lacked. Cutting those parts would leave the plan unable to show what happens on failure.

### Holes
- None.

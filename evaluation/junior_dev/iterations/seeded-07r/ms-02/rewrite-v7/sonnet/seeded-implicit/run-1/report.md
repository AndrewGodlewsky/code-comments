## Review of ms-02 (rewrite-v7, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Added opening summary and a Terms section (MailRelay, broker, flag, route, outbox relay, deliveries, notification types with daily volumes); no questions were shown, so these cover what a newcomer to the stack would need.
- Merged the one-line Notes (retries, dedupe, rollback, watching metrics) into a shared Rules section, the per-step text and a Rollback section; stated facts kept: 5 attempts with 1/2/4/8 minute backoff, separate databases, broker as only channel, idempotency key, rendering in the service, order and 3-day gaps, p99 under 60 s gate, 7-day decommission, rollback within a minute.
- Expanded step 3 into four service parts (consumer, sender, templates, metrics) with what starts each, where state lives and what happens on a crash.
- Defined the mechanism for dedupe (id as primary key in deliveries, ignore on conflict, acknowledge after insert) and for in-flight safety on rollback (route is stamped at enqueue, so each row finishes on its own side).
- Added the 24-hour key window check against the 15 minute maximum retry span, and the 10 s flag propagation.
- Split build steps from cutover steps and rollback; added a failure table.
- Added Open questions: template render failure handling and failed-status reporting back to the monolith, both undecided rather than invented.

### Holes
- None.

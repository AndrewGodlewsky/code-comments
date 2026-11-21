## Review of ms-02 (rewrite-v7, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Restructured into the required order: a three-sentence summary, a short description of how enqueue works today, terms, how the system runs, then the rollout steps in ship order, then open questions. The system description and the rollout are separate sections.
- Terms: defined the names a newcomer would not know (MailRelay, idempotency key, broker and at-least-once, outbox relay, route, runtime flag, deliveries table, p99, page on-call, notification row) and kept the notification types and volumes from the overview.
- Rollout step 7: replaced "once latency looks good" with the brief's exact gate (order_confirmed on the service for at least 3 days and p99 under 60 s shown on order_confirmed).
- Rollout step 8: the old worker is now removed only after password_reset has run on the service for 7 days, not as an unconditional step. Added the check that no monolith rows are still pending first, and that rollback ends at this step.
- Added the route and published_at columns (route defaults to monolith so existing rows stay with the old worker), the per-type flags, and the rule that the old worker takes only monolith rows. Decided: if the flag cannot be read, enqueue uses monolith.
- Added that the relay keeps publishing service-routed rows regardless of the flag, so a rollback finishes in-flight rows on the service without re-sending them. Rollback is described once, in How it runs.
- Added that the service acknowledges a message only after storing its row and keeps retry waits in its own table. Reason: the 1 to 8 minute waits exceed the broker's 30-second window.
- Duplicates are now explained in two layers (local record, then the MailRelay key) and cover crashes, redelivery, cutover and rollback. Each row has exactly one owner, fixed at enqueue time.
- Added the failure table covering the brief's failure cases (crash, broker down, MailRelay down, redelivery, service outage). Rollout steps point to the table for running-system failures, and each step lists its own step-specific failure handling.
- Restored every stated fact from the brief and the first version: 5 attempts, 1/2/4/8 minute backoff, timeouts as failures, the 50-row batch and 5-second poll, the 30-second broker window, the 10-second flag propagation, the 24-hour key window, the volumes, the cutover order and 3-day minimums, the old worker being kept deployable, the notification id as idempotency key on the old worker before any type moves, and the metrics to watch.
- Added open questions for the gaps the brief leaves open: broker retention, how the monolith row learns of service results, template drift during steps 3 to 8, the email address on the broker, and where the p99 clock starts.
- Length is well over 1.5 times the first version. This is deliberate: the brief's required facts (retry numbers, volumes, gates, rollback guarantees, per-step failure handling) had to be restored, and the rule against cutting stated facts takes precedence over the length target.
- No junior questions or answers were supplied with the task, so no answers were incorporated beyond the file's own content. The file was rewritten once from the first version and the brief, without tools.

### Holes
- None.

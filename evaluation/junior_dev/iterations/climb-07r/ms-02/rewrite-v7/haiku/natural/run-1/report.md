## Review of ms-02 (rewrite-v7, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Cut: the separate Core mechanisms section and the Assumptions bullets were merged into the summary, the terms and one 'How the system works' section, so each rule appears once.
- Cut: repeated retry, duplicate and failure wording from the steps was replaced by one rules list and one failure table. Each step keeps only its own start, data, state and on-failure lines.
- Cut: the Note under step 8 and the separate Changes lines in step 2 were folded into the steps they belong to. Open questions were shortened in wording and none were dropped.
- Added: the old worker's select now filters on `route = 'monolith'` in step 2. The plan previously required this only in the rollback section. Without it, the old worker would also send service-stamped rows, which causes duplicates during cutover.
- Changed: the flag is no longer cached once per process. It is cached for a few seconds. Caching it indefinitely would stop a rollback flip from taking effect within a minute.
- Clarified: the overdue check is defined as published more than 5 minutes ago with `receipt_at` still null. The receipt consumer's status change is stated as forward-only.
- Added: short term definitions for route, inbox, relay, lease, receipt, broker, ack, idempotency key, page on-call, bake, p99 and NTP. The reason for each mechanism is stated in one clause where it appears.
- Kept: every requirement, limit and number from the brief and the first version. This includes the cutover order, the 3-day bakes, the 60-second p99 gate, the 7-day decommission, the 5 attempts and 1/2/4/8 minute backoff, the 30-second broker redelivery, the 10-second flag propagation, the 24-hour key window, the 5-minute overdue threshold, the 30-minute receipt alert, the 15-minute exit check, the 53,500/day staging load and 3x peak, and the old-worker crash duplicate fact.

### Holes
- None.

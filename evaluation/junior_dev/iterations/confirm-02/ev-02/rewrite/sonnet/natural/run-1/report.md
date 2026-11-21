## Review of ev-02 (rewrite, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered into the skill layout: 2-3 sentence summary, terms, flowchart, then notes, steps, failure table, open questions. The diagram is kept verbatim.
- Added a Terms section defining event, subscription, delivery, attempt, dead, replay, claim, lease, lease_token, core DB, delivery DB, ack and libs/secrets.decrypt().
- Merged the Design choices section into the summary and short clauses: why Postgres schedules retries (queue delay cap of 15 min), why body is stored raw, why the claim re-checks the subscription, and why idempotent stages need no coordination.
- Merged the How the pieces work, Backoff, Outcomes, Disabled subscriptions and Dead letters sections into numbered Ingest and Dispatch steps plus an Admin API and purge list, so each rule appears once.
- Added the request details from the brief to dispatch step 5: raw body, 10 s timeout, X-Webhook-Id stability, signature format, and the 5-minute stale-t reason.
- Clarified the worker-lost rule: a row reclaimed from an expired lease with 8 attempts is dead-lettered without sending.
- Moved the disabled-subscription handling to the places it happens: dispatch step 3, the 410 outcome and the replay 409 rule. Added the failure-table row for subscriptions disabled while deliveries wait.
- Added at-least-once, no-ordering and several-instances statements under Guarantees and sharing the work.
- Moved the delivered-row 7-day purge and the disabled-subscription decision to Open questions, and added the unset queue dead-letter threshold N and alert owner.
- Removed the repeated duplicate-message and crash explanations from the failure table where they restated the steps, and removed the repeated lease-length sentence. No stated facts were dropped.

### Holes
- None.

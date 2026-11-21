## Review of ev-02 (rewrite, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-to-three sentence summary opening with how the system works today (events on domain-events, subscriptions in the core database) and why deliveries live in Postgres rather than the queue (15 min max delay vs 6 h retry; queue dead-letter topic cannot be listed or replayed).
- Added a terms section defining Event, Subscription, Delivery, Attempt, Dead, Ack, Claim, SKIP LOCKED and HMAC in one line each. This replaced the old bare component list.
- Added a where-state-lives section with the deliveries columns, the unique key, the read/update limits on the core database, and the rule that secrets are decrypted at send time and never copied.
- Expanded the diagram from a bare component chain into the whole path, with the dispatcher match, the dedupe insert and ack, the claim, the active-subscription check, the sign-and-POST step, each outcome class (2xx, retryable, 410, other 4xx), the 8-attempt check, the replay edge back to the table, the cleanup job, and the crash and database-error recovery edges.
- Replaced the vague note 'Workers use leases' with a single mechanism: claiming pushes next_attempt_at 60 s forward. There is no lease column, no lock and no takeover rule. The attempt is counted at claim time so a crash-looping delivery still ends dead after 8 claims.
- Replaced 'Disabled subscriptions are handled' with a concrete rule: a worker checks the subscription before sending and dead-letters with last_error 'subscription disabled'. This covers deliveries waiting when a 410 disables their subscription, with no sweep job.
- Added the retry-wait table (30 s, 2 min, 10 min, 30 min, 1 h, 3 h, 6 h, then dead). Added the exact header formats and the HMAC input, the 10 s timeout, the sign-on-every-attempt reason (receivers reject t older than 5 minutes), the full outcome list, and the 'attempt 1 within seconds' behaviour.
- Added the admin API behaviour: list dead deliveries with last status or error, and replay that keeps the id and resets attempts to 0. Replay is refused if the delivery is not dead or the subscription is disabled.
- Added a guarantees section (at-least-once, no ordering, no lost work) and a failure table covering dispatcher crash, queue dead-letter topic, worker crash before and after the POST, receiver failures, disabled subscriptions, and an unreadable core database.
- Added a separate short build and rollout section, kept apart from how the system runs.
- Added a stale-result guard: the result update applies only if the row is still pending with the same attempts value.
- Added open questions for 1xx/3xx handling, the 14-day retention of delivered rows (our choice), and the unchosen N for the queue's own dead-letter topic.
- Kept every requirement from the first version: dedupe on (event_id, subscription_id), HMAC signature plus webhook id header, 8 attempts on the agreed schedule, permanent failures straight to dead letter, 410 also disables the subscription, 14-day retention, replay, and cleanup job. Merged the first version's separate notes into the numbered steps so each fact is stated once.
- Note on length: the document is much longer than the first version. The first version was a list of components with almost no mechanism, and the brief's fixed requirements had to be carried into it.

### Holes
- None.

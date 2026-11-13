## Review of ms-02 (junior-v7, author sonnet, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Design in brief: defined attempts, next_attempt_at and the old worker's 'due' test, and described what enqueue_notification does for its caller (Q1, Q8).
- Design in brief: said the flags are the monolith runtime flags, who flips them, and that worker and relay read them on every batch (Q4).
- Design in brief: added a one-line MailRelay definition covering success, repeated key and error/timeout (Q3).
- Design in brief and step 3: listed the service status values and the exact 'due' rule including the lease (Q2).
- Step 3: consumer stores attempts and next_attempt_at unchanged; sender loop polls every 1 s and waits for a future next_attempt_at (Q7).
- Step 4: relay runs on every monolith instance, SKIP LOCKED behavior explained, and relay does not check next_attempt_at (Q1, Q5).
- Step 4: stated what the result is used for and what covers a missing result (Q6).
- Added an Open questions section: MailRelay call timeout versus the 60 s lease, how operators edit flags, whether anyone reads the final status (Q3, Q4, Q6).
- Step 3 sender loop: result_outbox is written only when a row becomes sent or failed, not after every attempt (Q9).
- Step 3 consumer: on an id that already exists and is sent or failed, queue a fresh result_outbox row, so a lost result reaches the monolith (Q10, a real gap).
- Step 4 reconciler and failure table: explain that republishing now recovers a lost result and the row leaves handed_off (Q10).
- Step 3 result publisher: state what happens when the broker is down or the publisher crashes before marking (Q11).
- Design in brief: state that the old worker holds the row lock through its MailRelay calls until the batch commits, and others skip those rows (Q12).
- Design in brief: added 'Who pages' bullet; result consumer is stated to never page; result topic payload (id and final status) specified (Q13).
- Failure summary: added the lost-or-duplicated result row and said the service pages on MailRelay failure.
- Step 4 relay: stated that the row lock is held until the relay's commit, which the race answer relies on.
- Step 4 result consumer: added the 'result arrives before the relay commits' case (wait on lock then apply; on rollback the republish re-queues the result; reconciler as backstop).
- Step 4 failure handling: added a pointer bullet for that race.
- Failure summary: added a row for a result arriving before the relay commits.
- Open questions: added that the lock-wait-then-recheck behaviour assumes PostgreSQL-like semantics and should be confirmed.
- Reorganised into the required order: summary (with how today's system works), terms, runtime flow, failure table, then a separate rollout section, then open questions.
- Merged the 'Design in brief' bullets and the component lists in steps 3 and 4 into one numbered runtime flow (enqueue, claim, hand off, receive, send, page, report back, reconcile), each with its trigger, state and failure handling, so each fact appears once.
- Added a terms section: monolith, service, broker (30 s redelivery, publisher confirm), MailRelay behaviour, old worker, relay, flag (10 s), row lock, attempts/next_attempt_at, lease.
- Kept answered-question additions: due-row rule, relay not checking next_attempt_at, relay on every instance, result_outbox only on final status, re-queued result on duplicate id, who pages, lock held by old worker, result-before-commit race.
- Rollout steps 3, 4, 6, 7, 8 now refer to the runtime flow instead of repeating component lists and failure bullets; step 6 restates rollback within the one-minute requirement.
- Cut repeated explanations of the three duplicate-prevention layers into one short paragraph, and removed repeated rollback and broker-down wording from steps 6 and 8 (kept the key point).
- Kept all stated numbers and rules: 5 attempts, 1/2/4/8 backoff, key on old worker first, order of types, 3-day holds, p99 under 60 s gate, 7-day hold and decommission, 30 duplicates a week, 24 h window, alert thresholds (1 h, 30 s, 45 s over 15 min), 60 s lease, 1 s polls, 40,000/12,000/1,500 per day.
- Open questions unchanged in content (MailRelay timeout, flag editing, who reads final status, database lock behaviour).

### Holes
- None.

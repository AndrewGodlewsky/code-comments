## Review of ms-02 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Gave every step the four parts the brief asks for: what starts it, what data moves, where state lives, and what happens on failure. The original gave one line per step.
- Added a Terms section that defines notification, enqueue, broker (at-least-once, 30 s redelivery), MailRelay (idempotency key, 24-hour window), route, flag and the retry policy, for readers who do not know the project.
- Stated that the route is written on the row at enqueue time and never changed by later flag flips. This is what makes rollback neither lose nor re-send in-flight notifications.
- Replaced the vague 'Dedupe on notification id' with the concrete rules: insert-or-ignore on id, and acknowledge only after commit, which keeps acknowledgement inside the 30 s window while retries wait in the service's own database.
- Added the 24-hour rule: a row whose last send is older than the MailRelay key window and has no result is marked failed and paged instead of re-sent.
- Replaced 'once latency looks good' with the explicit gate from the brief, and added the 3-day minimum for each move.
- Added the outcome path (service to monolith) so the monolith's table reflects final status, with a forward-only update that tolerates repeats.
- Added a rollback section that applies to steps 5 to 7, and noted that rollback needs the old worker and ends when it is removed.
- Added checks to run during each move (relay backlog, failed count, p99 latency, reconciliation, duplicate reports).
- Added open questions on broker retention, retention of deliveries rows, and personal data on the broker.
- Corrected a typo in the rollback section that was left in during drafting.
- Fixed a typo in the Rollback section: 'monolist... to monolith' is now a single clear instruction.
- Defined the terms a reader outside this project may not know: outbox, lease, forward-only update, golden test, FOR UPDATE SKIP LOCKED, and p99.
- Expanded the Broker term to explain acknowledgement and the 30 s window, and the MailRelay term to explain why a repeated send is safe.
- Step 1: stated that the key only prevents duplicates within MailRelay's 24-hour window.
- Step 2: stated that a flag-store failure still lets the enqueue succeed.
- Step 3: spelled out the consumer, sender, and templates parts, and what the sender's lease and claim mean.
- Step 4: clarified the relay and outcome consumer as separate data flows.
- Step 6: defined how enqueue-to-MailRelay latency is measured, using created_at and the accepted time.
- Step 8: listed the removal steps as a numbered list and stated that removing the worker makes rollback slower.
- Rollback: said the switch takes effect within about a minute overall, and separated rows not yet handed off (in the monolith table) from rows already on the broker.
- Checks: the failed count now covers both the monolith notifications table and the service deliveries table.
- Open questions: explained why broker retention matters to the 24-hour rule, and how it could allow duplicates.
- Added a plain-language opening paragraph that says what is moving, why, and what stays the same for business code.
- Defined terms the draft used without explanation: at-least-once, acknowledge, idempotency key, lease, forward-only update, route, outbox, golden test, and p99.
- Explained the 'FOR UPDATE SKIP LOCKED' clause in step 3 as a database instruction that skips rows another worker has locked.
- Explained the p99 latency target in step 6 so a reader knows what the 60 s threshold means.
- Split long bullets and compound sentences into shorter ones, without changing the meaning.
- Reworded step 8's first check to say 'no row routed to the monolith is still waiting to be sent', which is clearer than the field-name form.
- Kept every step, its order, all thresholds (5 attempts, 1/2/4/8 minute backoff, 3-day and 7-day holds, 60 s p99, 24-hour key window, 30 s acknowledgement window), the rollback rules, the checks, and the open questions unchanged.

### Holes
- None.

## Review of ms-02 (junior-v6, author sonnet, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Rewrote the whole file in the required order: summary, terms, numbered runtime steps, failure table, rollout order, rollback, open questions.
- Added how the monolith works today and the three types with volumes, since the junior asked what the worker sends and how it is handed work.
- Defined MailRelay, idempotency key, broker, flag, route, outbox and deliveries in the terms.
- Specified the outbox relay: the notifications table is the outbox, the row is marked handed_off after broker confirmation, and republishing is absorbed by the service.
- Specified the message fields and the service intake and sender, committing per row instead of per batch to avoid the old duplicate problem.
- Spelled out the retry policy (5 attempts, 1/2/4/8 minute waits, then failed and page on-call) and who owns its state.
- Decided that route is set once at enqueue so rollback only affects new rows, and that in-flight rows stay with the service, so no double send.
- Gave the reason for the cutover order and the p99 under 60 s gate, plus 3-day dwell per type and 7-day wait before removing the old worker.
- Defined where metrics come from (service for latency and failures, monolith for relay backlog).
- Added two open questions: rows stranded by a broken service on rollback, and where metrics are stored.
- Step 3: relay now runs on every monolith instance, uses the row lock, polls every 1 s, takes up to 50 rows per pass, and commits handed_off in one transaction (answers Q10, Q11).
- Step 3: stated that the monolith never learns the outcome and that deliveries by id is where to look (Q15).
- Step 5: sender polls every 1 s, row lock released on instance death so another instance takes the row, 10 s MailRelay timeout (Q12, Q13, Q14).
- Step 6: stated that a waiting row stays pending with a future next attempt time (Q14).
- Step 7: said the 60 s latency target includes both polls and the broker hop (Q13).
- Terms: added handed_off and row lock; defined deliveries statuses; clarified outbox.
- Failure table: relay row now says dies before commit; added service dying mid-send.
- Open questions: added that the monolith's current MailRelay timeout is unknown.
- Step 5: a sender pass now keeps taking due rows until none are due, then waits 1 s, so bursts drain (Q16).
- Step 3: the relay waits up to 10 s for confirmations and marks only confirmed rows handed_off; unconfirmed rows stay pending and are republished next pass (Q17).
- Failure table: added a row for partial or missing broker confirmation (Q17).
- Reordered into summary, terms, how it runs, failure table, rollout, rollback, open questions; kept how the system runs separate from rollout.
- Merged the repeated 'crash then service ignores the copy' explanations in relay and sender steps into single statements per step; kept both in the failure table.
- Shortened the intro by trimming wording; kept the explanation of how the system works today.
- Removed cross-step pointers like 'step 4' and replaced with plain descriptions.
- Reworded step 7 metrics to list relay poll, broker hop and sender poll plainly instead of 'both 1-second polls'.
- Rollback now says 'marked service' instead of 'stamped'; the required one-minute limit is stated as required.
- Kept every stated fact: 5 attempts, 1/2/4/8 backoff, 3-day and 7-day holds, order of types, p99 under 60 s, 24 h window, 30 s redelivery, 10 s flag propagation, volumes, 30 duplicates a week.
- Added nothing new; no details dropped beyond wording.

### Holes
- None.

## Review of ev-02 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Added a short opening paragraph that explains the context: what the core app and outbox relay already do, and what this service adds.
- Expanded the components line into plain sections (state, dispatch, sending and retries, crash recovery, dead letters, disabled subscriptions) so each step has its own heading.
- Defined terms a newcomer would not know: outbox, lease, dead letter, HMAC-SHA256 signing, at-least-once delivery, and the `ON CONFLICT` dedupe.
- Stated where state lives: the `deliveries` table in the service's own database, with the columns it holds and the rule that the queue is not relied on for state.
- Explained why retries use `next_attempt_at` and polling instead of queue delays (the 15-minute queue limit versus the 6-hour final wait).
- Specified the dedupe key and the order of insert then ack, and what happens on a redelivered message.
- Specified the claim, lease and crash rules: the 60 s lease versus the 10 s timeout, that a crashed attempt still counts, and that receivers dedupe on X-Webhook-Id.
- Replaced the vague note 'Disabled subscriptions are handled' with concrete rules: a check before every send, and dead-lettering of pending rows on a 410.
- Specified that replay is refused for a disabled subscription, and that delivered rows fall outside the 14-day rule and need their own retention decision.
- Gave the total retry span (about 10 h 43 min to attempt 8) and stated that waits start when the failed attempt ends.
- Rebuilt the Mermaid flowchart to show the subscription check, the claim step, lease expiry after a crash, the 410 branch, the exhausted-attempts branch, and the replay and cleanup paths. Renamed the dead-letter node so it is not confused with the queue's own dead-letter topic. Kept it a flowchart as the brief requires.
- Added a short opening that says what the service does and where the events come from, so a reader new to the project can follow it.
- Added a short list of terms (delivery, claim, lease, dead letter, at-least-once) and explained each one where it first matters.
- Explained that the service connects to the core database only to read subscriptions and to update two status columns, and that the two databases cannot share a transaction.
- Changed the 410 step from 'in the same transaction' to an ordered sequence: update the core subscription first, then dead-letter locally. A crash between the two is repaired by the pre-send check. The original wording could not be implemented across two databases.
- Added the replay refusal to the diagram. The text said replay is refused while disabled, but the chart did not show it.
- Stated that replay sets next_attempt_at to now, so a replayed row is due immediately.
- Added that the Dispatcher's ack must happen within the 30 s visibility timeout, and why a late ack is harmless.
- Added what happens to a row that is already in_flight when its subscription is disabled.
- Explained the claim step in plain words (SKIP LOCKED, lease, no open transaction during the HTTP call) and the schedule arithmetic, and split long sentences. All rules, numbers, node meanings and the diagram structure are unchanged apart from the two additions above.
- Added a plain-language opening that explains the outbox, the relay, the queue and the purpose of the service, for a reader who does not know the project.
- Defined the terms Delivery, Dispatcher, Worker, Claim, Lease, Dead letter and At-least-once in one short list before they are used.
- Simplified the Mermaid flowchart labels into plain words and kept the same nodes and paths, so the flow reads without the surrounding text. The 410 node now says the row is dead first, then the subscription is disabled.
- Split the 'Where state lives' section into a list of what each row holds and a separate paragraph on the two databases, and explained why the steps are ordered as they are.
- Reworded the dispatch, retry and replay sections into shorter sentences and spelled out what the lease, the claim and SKIP LOCKED do.
- Stated the signing rule explicitly: the signature is HMAC-SHA256 over the text t followed by a dot and the stored body, using a fresh t on every attempt.
- Noted the open question about retention of delivered rows, which the source document raised but the brief did not settle.
- Kept the format: a Mermaid flowchart followed by short notes. No requirements were changed.

### Holes
- None.

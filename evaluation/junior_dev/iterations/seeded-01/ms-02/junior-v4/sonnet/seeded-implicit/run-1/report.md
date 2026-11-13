## Review of ms-02 (junior-v4, author sonnet, seeded-implicit)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a summary of how notifications work today and how the new flow goes, plus a terms list, because the junior did not know MailRelay, route, outbox or the broker.
- Split the document into how it runs, a failure table and the rollout order, since the original mixed building with running.
- Defined route as stamped once at enqueue time from the flag, with a published_at column, so rollback and cutover cannot double send.
- Spelled out the outbox relay, consumer and sender steps, including what each does when the broker, MailRelay or the service fails, using the simplest handling (retry next pass, redelivery, same key).
- Replaced 'Retries: same policy as today' and 'Dedupe on notification id' notes with the actual policy and the two places dedupe happens.
- Wrote the rollback behaviour for in-flight rows and the 3 day, 7 day and p99 under 60 s gates into the rollout steps.
- Added two open questions: dashboard location and rollback while the service is broken.
- Step 3: stated that the relay runs on every monolith instance and claims rows with FOR UPDATE SKIP LOCKED; duplicates after a crash are absorbed by the consumer.
- Step 5: stated that several sender instances may run, claim rows with FOR UPDATE SKIP LOCKED and commit per row; double sends are dropped by the MailRelay key.
- Failures table: widened the redelivery and resend rows to cover double publish and two senders on one row.
- Reordered into the newcomer layout: summary, terms, steps, failures, rollout, rollback, open questions.
- Gave every step in How it runs the same four parts: starts, does, data, on failure.
- Cut the Relay backlog term and defined it inline in the outbox relay step.
- Merged the broker-only-link sentence into the Broker term and shortened the Status step.
- Dropped the claim that the old worker uses the same loop as today in favor of one plain description, and removed the duplicated MailRelay type table detail from terms.
- Corrected rollback timing wording to match the 10 s flag propagation fact.
- Kept rollout and rollback separate from how the system runs; kept open questions at the end.

### Holes
- None.

# Plan: extract notifications into a Notification Service

Today the monolith sends notifications itself. Business code calls `enqueue_notification(tx, ...)` inside its own transaction, which inserts a `pending` row into the monolith's `notifications` table. A worker thread on every monolith instance picks up due rows in batches, renders the template, sends through MailRelay, and commits once per batch. This competes with checkout for CPU and database connections.

The new plan keeps callers unchanged. A per-type flag decides, when the row is created, whether the old worker or a separate Notification Service sends it. Rows for the service travel through the message broker. The service has its own database and does the rendering, sending and retrying. Types move to the service one at a time.

## Terms

- **MailRelay**: the email provider. It is called with `send()`.
- **Idempotency key**: an optional `send()` argument. If MailRelay accepted a send with the same key in the last 24 hours, it drops the new one and returns success. We always pass the notification id.
- **Notification**: one email for one user from one event. It has an id, type, email and payload. The types are `shipping_update` (40,000/day), `order_confirmed` (12,000/day) and `password_reset` (1,500/day, needs p99 enqueue-to-MailRelay under 60 s).
- **Route**: a column on the monolith row, `monolith` or `service`. It is set once, at enqueue, from the flag `notify.route.<type>`. A flag change reaches every monolith instance within 10 s.
- **Outbox relay**: a loop in the monolith that publishes `service` rows to the broker topic `notifications.requested`.
- **Broker**: the shared message broker, and the only link between the two databases. It is at-least-once: a message not acknowledged within 30 s is redelivered, possibly to another consumer. A publisher gets a confirmation once the broker has stored the message.
- **Deliveries**: the service's own table, one row per notification, keyed by notification id.

## How it runs

Each step lists what starts it, what it does, where its data lives, and what happens on failure.

1. **Enqueue**
   - Starts: business code calls `enqueue_notification`.
   - Does: reads the type's flag and writes `route` into the new row, in the caller's transaction.
   - Data: the monolith `notifications` table.
   - On failure: if the transaction fails, no row exists and nothing is sent.

2. **Old worker**
   - Starts: its polling loop, on every monolith instance, as today.
   - Does: picks only `route = 'monolith'` rows, renders, sends with the notification id as the idempotency key, and commits once per batch, as today. Retries follow the policy below.
   - Data: the monolith `notifications` table.
   - On failure: after a crash, rows from the uncommitted batch are sent again, and MailRelay drops the repeats.

3. **Outbox relay**
   - Starts: a timer, every few seconds, on every monolith instance.
   - Does: claims a batch of `route = 'service'` rows with `published_at` empty, using `FOR UPDATE SKIP LOCKED`. It publishes each row to the broker and sets `published_at` once the broker confirms.
   - Data: the monolith `notifications` table.
   - On failure: if the broker is down, rows stay unpublished and are retried on the next pass. The number of unpublished rows (the backlog) grows and raises an alert. If an instance crashes between publishing and marking, the row is published twice, and step 4 absorbs that.

4. **Consumer**
   - Starts: a broker message arrives.
   - Does: inserts a `deliveries` row (id, type, email, payload, `status = pending`, `attempts = 0`, `next_attempt_at = now`, original created time), commits, and only then acknowledges. If the id already exists, it skips the insert and acknowledges.
   - Data: the service database, `deliveries`.
   - On failure: if the service crashes before the commit, the broker redelivers after 30 s.

5. **Sender**
   - Starts: a polling loop on each service instance. Several instances may run it.
   - Does: claims due `pending` rows with `FOR UPDATE SKIP LOCKED` and commits after each row. It renders the template and calls MailRelay with the notification id as the key. On success it marks the row `sent` and records the enqueue-to-MailRelay latency.
   - Data: the service database, `deliveries`.
   - On failure: on a MailRelay error or timeout, it applies today's retry policy: 5 attempts, waits of 1, 2, 4 and 8 minutes before attempts 2 to 5, then `failed` and a page to on-call. If two instances send the same row, or one crashes after MailRelay accepted but before the commit, MailRelay drops the resend because the key matches. All retries fall inside its 24 hour window.

6. **Status**
   - The service never writes back to the monolith. The monolith row stays as published, and `sent` or `failed` lives only in `deliveries`.

Nothing is lost: every committed row is either sent by the old worker, or relayed, stored in `deliveries`, and then sent or marked failed with a page. Nothing is duplicated: a row has one route, `deliveries` is unique on id, and MailRelay drops repeated keys.

## Failures

| Failure | What happens |
|---|---|
| Broker down | The relay cannot publish. Rows wait unpublished and are retried. The backlog alert fires. |
| Message redelivered or published twice | The consumer finds the existing `deliveries` id and acknowledges. |
| Service crash | Unacknowledged messages are redelivered. The sender resumes from `deliveries`. |
| MailRelay down or slow | The sender retries per policy, then `failed` and a page. |
| Resend after a crash, or two senders on one row | MailRelay drops it, same key. |

## Rollout, in order

1. Pass the idempotency key in the old worker and ship it alone. This also stops today's weekly duplicates.
2. Add the `route` and `published_at` columns (default `monolith`) and the three flags, all off. The old worker filters on `route`.
3. Build and deploy the service: database, consumer, sender, templates, and latency and failure metrics.
4. Deploy the outbox relay in the monolith. No flag is on, so it publishes nothing.
5. Turn on `shipping_update`. Run at least 3 days, watching backlog, failed counts and latency.
6. Turn on `order_confirmed`. Run at least 3 days. Its p99 enqueue-to-MailRelay must be under 60 s before the next step.
7. Turn on `password_reset`. It goes last because it is the only type with a latency requirement, and we want proof first.
8. After `password_reset` has run on the service for 7 days, check that no `monolith` rows are pending, then remove the old worker. Until then keep it deployable.

## Rollback (any type)

Turn the type's flag off. New notifications go to the old worker within about 10 s. Rows already routed to the service finish there, so nothing is lost or sent twice, and the service must keep running until they are done. Rows already on the old worker are never sent by the service, because each row has one route.

## Open questions

- Where the latency, backlog and failed-count dashboards and alerts live is not decided.
- If the service is broken at rollback time, its in-flight rows wait until it recovers. This is not handled.
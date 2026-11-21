# Plan: extract notifications into a Notification Service

Today the monolith records each notification in its `notifications` table, and a worker thread on every instance sends it through MailRelay. That competes with checkout for CPU and database connections. We will add a separately deployed Notification Service with its own database. The monolith keeps recording notifications and publishes them through the broker, and the service sends them. We move one type at a time behind flags, so any type can go back with a flag flip.

## Terms

- **Notification**: one email, identified by its id (a uuid made in `enqueue_notification`). The three types are `shipping_update` (about 40,000 a day), `order_confirmed` (12,000 a day) and `password_reset` (1,500 a day, which must reach MailRelay within 60 s at p99).
- **MailRelay**: the email provider. `send()` takes an optional `idempotency_key`. If it already accepted that key in the last 24 hours, it drops the new send and returns success.
- **Broker**: the shared message broker. It is at-least-once. A message not acknowledged within 30 s is redelivered, possibly to another consumer. A publisher gets a confirmation once the message is stored. It is the only link between the monolith and the service.
- **Flag**: `flags.get(name)` in the monolith. A change reaches every instance within 10 s. We use one per type, `notify.route.<type>`.
- **Route**: a new column on `notifications`, either `monolith` or `service`. `enqueue_notification` sets it from the type's flag when it inserts the row. Callers do not change.
- **Outbox relay**: a new loop in the monolith that publishes `route = service` rows to the broker topic `notifications.requested`.
- **Deliveries**: the service's table, with one row per notification. The notification id is its primary key.

## Rules that hold in every step

- The service never reads or writes the monolith database, and the monolith never touches the service database.
- Every send passes the notification id as `idempotency_key`. This is what stops a duplicate email after a crash or a redelivery.
- Retry policy is today's: 5 attempts, waits of 1, 2, 4 and 8 minutes before attempts 2 to 5, then mark `failed` and page on-call. The old worker and the service both follow it.
- Every notification whose enqueuing transaction committed ends up accepted by MailRelay, or `failed` with on-call paged.

## Build steps (no user traffic changes until step 5)

1. **Add idempotency keys to the old worker.**
   - Starts: a deploy of the monolith.
   - Does: `_deliver` calls `mailrelay.send(..., idempotency_key=row.id)`.
   - State: the `notifications` table, as today.
   - If it goes wrong: a worker that dies after MailRelay accepted a send re-sends the row, and MailRelay drops it. This ends the roughly 30 duplicate emails a week. The last retry comes about 15 minutes after the first, well inside the 24-hour key window.
2. **Add the route column and flags.**
   - Starts: a monolith deploy with a migration.
   - Does: adds `notifications.route`, default `monolith`. `enqueue_notification` sets it to `service` when the type's flag is on. The old worker only picks up `route = monolith` rows. All flags start off, so nothing changes yet.
   - State: the `notifications` table and the flags.
3. **Build the Notification Service.** It has four parts, all keeping their data in the `deliveries` table:
   - **Consumer.** Starts on each broker message. It inserts a `deliveries` row (id, type, email, payload, `pending`, 0 attempts, due now), ignoring the insert if the id exists. Then it acknowledges the message. If the service crashes before the acknowledge, the broker redelivers and the insert is ignored.
   - **Sender.** Starts on a poll for due `pending` rows. It renders the template, calls `send` with the id as the key, and commits per row, not per batch. On success it sets `sent`. On a MailRelay error, including a timeout, it applies the retry policy above. A crash after MailRelay accepted a send but before the commit leaves the row `pending`. The next send is dropped by MailRelay and the row becomes `sent`.
   - **Templates.** Rendering moves here from the monolith.
   - **Metrics.** It reports enqueue-to-MailRelay latency per type and failed counts.
4. **Add the outbox relay to the monolith.**
   - Starts: a poll for rows with `route = service` and no `published_at`.
   - Does: publishes each row (id, type, email, payload) and waits for the broker's confirmation. Then it sets `published_at` on that row.
   - State: the `notifications` table. The monolith does not track delivery after publishing, because the service owns that.
   - If it goes wrong: while the broker is down, the rows stay unpublished and the relay keeps retrying, so nothing is lost. A crash after the confirmation but before `published_at` publishes the row again. The service ignores the second copy.
   - Watch relay backlog (unpublished rows).

## Cutover steps

Each move is one flag flip. A flip reaches all monolith instances within 10 s. Rows enqueued during those seconds go to either side, and both are safe because of the idempotency key. Rows already stamped `service` before a rollback stay with the service and finish there, and rows stamped `monolith` finish on the old worker. So an in-flight notification is never lost and never sent twice. During every move, watch relay backlog, failed counts and p99 latency.

5. **Move `shipping_update`.** Turn `notify.route.shipping_update` on. Let it run on the service for at least 3 days.
6. **Move `order_confirmed`.** Turn its flag on. Let it run for at least 3 days. Its p99 enqueue-to-MailRelay latency must stay under 60 s.
7. **Move `password_reset`.** Do this only once step 6 has shown p99 under 60 s on `order_confirmed`, and after the 3 days.
8. **Remove the old worker.** Keep it deployable until `password_reset` has run on the service for 7 days. Then delete it.

## Rollback

Set the type's flag off. It takes effect within a minute (in practice within 10 s). New notifications go to the old worker, and in-flight ones finish where they are, as described under Cutover. The old worker must stay deployable until step 8.

## What happens when things fail

| Failure | Result |
|---|---|
| Broker down | The relay keeps retrying and the rows stay unpublished. Nothing is lost. |
| Relay crashes after the broker confirmed | The message is published again and the service ignores the duplicate id. |
| Message redelivered | The insert is ignored because the id already exists. |
| Service crashes before the acknowledge | The broker redelivers and the insert succeeds or is ignored. |
| Service crashes after MailRelay accepted a send | The send is repeated and MailRelay drops it, since the key is the same. |
| MailRelay down or timing out | Retry with 1, 2, 4 and 8 minute waits. After 5 attempts, mark `failed` and page on-call. |
| Old worker dies mid-batch | Its rows stay `pending` and are re-sent with the same key, so MailRelay drops the duplicates. |

## Open questions

- If a template fails to render, we plan to count it as a failed attempt under the same retry policy. The brief does not say.
- How the service's `failed` rows are reported back to the monolith, if at all, is not decided. The brief only requires the page.
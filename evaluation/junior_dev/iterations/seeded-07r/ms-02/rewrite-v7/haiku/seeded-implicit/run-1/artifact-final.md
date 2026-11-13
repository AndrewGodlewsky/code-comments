# Plan: extract notifications into a Notification Service

## Summary

Today the monolith sends every notification from its own table, which competes with checkout for CPU and database connections. This plan moves sending into a separately deployed Notification Service with its own database. The monolith still records each notification, and a relay sends the ones routed to the service through the broker, one type at a time behind flags, so rollback is a flag flip.

Today, `enqueue_notification` inserts a `pending` row inside the caller's transaction, and a worker on every monolith instance sends pending rows in batches of 50, committing once per batch. A crash after MailRelay accepts part of a batch but before that commit makes the worker send those rows again, which causes about 30 duplicate emails a week.

## Terms

- **Notification row**: one row in the monolith's `notifications` table. It is one email to one user.
- **MailRelay**: our email-sending provider. We call its `send()` function.
- **Idempotency key**: a string sent with each `send()`. If MailRelay already accepted a send with the same key in the last 24 hours, it drops the new send and reports success. We use the notification id as the key.
- **Broker**: the message system that billing and search already use. It is at-least-once: a message not acknowledged within 30 seconds is redelivered, possibly to a different consumer. A publisher gets a confirmation once the broker has stored the message.
- **Outbox relay**: a loop in the monolith that publishes rows routed to the service as broker messages.
- **Route**: `monolith` or `service`. It is set on each row when the row is enqueued, and it says which side sends that row.
- **Runtime flag**: a monolith setting read with `flags.get(name)`. A change reaches every monolith instance within 10 seconds. `notify.route.<type>` is the route flag for one type.
- **deliveries table**: the service's own table of notifications it has accepted, keyed by notification id.
- **p99**: the time within which 99 out of every 100 notifications finish.
- **Page on-call**: `alerts.page_oncall`, which alerts the engineer on call.

The notification types are `shipping_update` (about 40,000 a day), `order_confirmed` (about 12,000 a day) and `password_reset` (about 1,500 a day). All three are email through MailRelay. `password_reset` also needs p99 enqueue-to-MailRelay under 60 seconds.

## How it runs

### Enqueue (monolith, unchanged for callers)

Business code (checkout, the carrier webhook, password reset) calls `enqueue_notification(tx, user, type, payload)` inside its own transaction. The function inserts the row with status `pending` and sets `route` from `notify.route.<type>`. If the flag cannot be read, the route is `monolith`. The row exists only if the caller's transaction commits. Callers do not change.

### Monolith sending (route = monolith)

The existing worker keeps today's loop. It polls every 5 seconds and takes only `pending` rows with route `monolith`. For each row it renders the template, calls MailRelay with the notification id as `idempotency_key`, and records the outcome. It still commits once per batch, and the key stops the duplicate sends that this causes.

### Relay and broker (route = service)

The outbox relay polls for rows with route `service` and no `published_at`. For each one, it publishes a message to topic `notifications.requested` with the notification id, type, user email, payload and creation time. It sets `published_at` only after the broker confirms the message. Row locks stop two instances from publishing the same row. The relay keeps publishing `service` rows whatever the flag says, so rows already routed to the service still get delivered after a rollback.

### Service (route = service)

The service has its own database. It never reads or writes the monolith's database, and the broker is the only channel between them.

1. The consumer takes a message and inserts a row into `deliveries` keyed by notification id. If the id already exists, it skips the insert. Then it acknowledges the message.
2. The sender loop picks `pending` `deliveries` rows that are due, renders the template (templates now live in the service), and calls MailRelay with the notification id as `idempotency_key`.
3. On success it sets the row to `sent` and stores `accepted_at`. On failure it follows the retry policy.

The service acknowledges a message only after its row is stored. The retry waits (1 to 8 minutes) are longer than the broker's 30-second window, so the service must not hold a message while it waits. The wait is kept in the service's own table instead.

### Retry policy (same on both sides)

- Up to 5 attempts. A timeout counts as a failure.
- Wait 1 minute before attempt 2, 2 minutes before attempt 3, 4 minutes before attempt 4, and 8 minutes before attempt 5.
- If attempt 5 fails, set the row to `failed` and page on-call.

The monolith keeps `attempts` and `next_attempt_at` on the notification row. The service keeps the same two fields in `deliveries`.

### Nothing lost

A notification whose transaction committed is in the monolith's table. The relay keeps retrying the publish until the broker confirms it, and the service keeps retrying sends until MailRelay accepts or the row is marked failed and on-call is paged.

### Nothing duplicated

- Each row has one owner. Its route is fixed when it is enqueued, so the monolith worker and the relay never take the same row.
- The local record stops a repeated broker message from causing a second send: the `deliveries` table on the service side, and the `published_at` mark on the monolith side.
- The MailRelay idempotency key stops a second send after a crash between "MailRelay accepted" and "row recorded." The key is the notification id on both sides, so it also covers a row sent by one side and then retried by the other within 24 hours. All retries together take about 15 minutes, well inside that window.

### Rollback

Flip `notify.route.<type>` back to `monolith`. New rows of that type get the monolith route within about 10 seconds. Rows already routed to the service stay there: the relay keeps publishing them and the service finishes them. Nothing is re-sent, because each row still has one owner. Rollback needs the old worker, so it is possible only until rollout step 8.

### When things fail

| Event | What happens |
|---|---|
| The caller's transaction rolls back | No row and no message. Nothing is sent. |
| Monolith crashes after the enqueue commits | The row stays `pending`. After restart, the monolith worker or the relay picks it up, depending on its route. |
| Relay crashes after publishing but before setting `published_at` | The row is published again. The service finds the id in `deliveries` and skips it. |
| Broker is down | The relay cannot publish. Rows stay unpublished and the relay retries. Monolith sending is not affected. |
| Service consumer crashes before acknowledging | The broker redelivers after 30 seconds, possibly to another consumer. The stored row makes the redelivery a no-op. |
| Service crashes after MailRelay accepts but before recording `sent` | The row is still `pending` after restart, so it is sent again with the same key. MailRelay drops the repeat. |
| Broker redelivers a message | The insert finds the existing id and skips it. No second send. |
| MailRelay is down or times out | Each attempt counts, and the retry policy applies. After 5 failures the row is marked `failed` and on-call is paged. |
| Monolith worker crashes mid-batch | Uncommitted rows stay `pending`. The idempotency key stops the duplicate sends for rows that MailRelay already accepted. |
| Service is down for a long time | Messages wait in the broker. How long it keeps them is not known (see open questions). |

## Rollout (ship order)

Each step says what starts it, what data moves, where the state lives, and what happens if it fails. Failures while the system is running are covered in the table above.

1. **Add idempotency keys to the old worker.**
   - Starts: deploy of the monolith change.
   - Data moves: nothing. Each send passes the notification id as `idempotency_key`.
   - State: no table changes.
   - If it fails: the old worker keeps sending without keys, so the duplicate risk stays until the change deploys. After this step, expect the about 30 weekly duplicates to stop. Check that count to confirm.

2. **Add the route and `published_at` columns, and the flags.**
   - Starts: database migration, then deploy.
   - Data moves: none. `route` defaults to `monolith`, so existing pending rows stay with the old worker. `published_at` is nullable. Create `notify.route.<type>` for the three types, all set to `monolith`.
   - State: the monolith database.
   - Code: enqueue sets `route` from the flag. The old worker takes only `monolith` rows. Every instance must run this worker change before any flag is flipped, which step 5 guarantees.
   - If it fails: a failed migration changes nothing. If the flag cannot be read, enqueue sets `monolith`, so the current behavior continues.

3. **Build the Notification Service.**
   - Starts: deploy of the new service with its own database.
   - Data moves: none yet. The service has the `deliveries` table, the broker consumer, the sender, and copies of the templates.
   - State: the service database only.
   - If it fails: nothing routes to the service yet, so the monolith is not affected.

4. **Add the outbox relay in the monolith.**
   - Starts: deploy of the relay loop on the monolith instances.
   - Data moves: rows with route `service` and no `published_at` become messages on `notifications.requested`.
   - State: `published_at` on the monolith rows.
   - If it fails: see the table. With no `service` rows, the relay publishes nothing.

5. **Move `shipping_update`.**
   - Starts: flip `notify.route.shipping_update` to `service`.
   - Data moves: new `shipping_update` rows get route `service`. Rows already pending stay with the old worker.
   - State: monolith rows, `published_at`, and the service's `deliveries` table.
   - Run it on the service for at least 3 days. Watch relay backlog, failed counts and enqueue-to-MailRelay latency.
   - If it fails: flip the flag back to `monolith` (see Rollback).

6. **Move `order_confirmed`.**
   - Starts: flip `notify.route.order_confirmed` to `service`, only after `shipping_update` has run on the service for at least 3 days.
   - Data moves, state and failure handling: as in step 5.
   - Run it for at least 3 days, and watch the same three measures. Its p99 enqueue-to-MailRelay latency must be under 60 seconds before step 7.
   - If it fails: flip back to `monolith`.

7. **Move `password_reset`.**
   - Starts: flip `notify.route.password_reset` to `service`, only after both are true: `order_confirmed` has run on the service for at least 3 days, and the service has shown p99 enqueue-to-MailRelay latency under 60 seconds on `order_confirmed`. The latency is measured from the creation time in the message to `accepted_at`.
   - Data moves, state and failure handling: as in step 5.
   - If it fails: flip back to `monolith`.

8. **Remove the old worker.**
   - Starts: 7 days after `password_reset` has been running on the service. Until then, keep the old worker deployable, because rollback needs it.
   - Before removing it, check that no `monolith` rows are still `pending`.
   - Data moves: none.
   - Removes: the old worker code and its thread, and the monolith copies of the templates. The relay and the service stay.
   - If it fails: keep the old worker deployed. After this step, rollback is no longer possible.

## Open questions

- How long does the broker keep a message that no consumer has acknowledged? This sets how long a service outage can last without loss.
- How does the monolith's `notifications` row learn that the service sent or failed a notification? Failed counts are read from that table today, and the brief names no result channel.
- Templates exist in both places until step 8. Who makes sure a template change reaches both?
- Each message carries the user's email address. Confirm the broker may carry it.
- Does the p99 latency clock start at enqueue inside the caller's transaction, or at commit?
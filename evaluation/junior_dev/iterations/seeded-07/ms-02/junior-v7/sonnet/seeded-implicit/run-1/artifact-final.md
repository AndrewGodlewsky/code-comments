# Plan: extract notifications into a Notification Service

Today the monolith writes a `notifications` row inside the caller's transaction (`enqueue_notification`). A worker thread on every monolith instance, every 5 s, locks up to 50 due pending rows, renders each template, sends it through MailRelay and updates the row, committing once per batch. That competes with checkout for CPU and database connections. The new flow keeps the same enqueue call and table. A per-type flag stamps each new row with a route, and rows routed to the service are published to the broker by an outbox relay, stored in the service's own database and sent from there. Types move one at a time, and the old worker stays as the rollback path.

## Terms

- **MailRelay**: the email provider we call with `send()`. Given an `idempotency_key`, it drops any send with a key it accepted in the last 24 hours and returns success. Today we pass no key.
- **Broker**: the shared message system (also used by billing and search). It is at-least-once. A message not acknowledged within 30 s is redelivered, possibly to another consumer. A publisher gets a confirmation once the broker has stored the message. Our topic is `notifications.requested`.
- **Flag**: `flags.get(name)` in the monolith. A change reaches every monolith instance within 10 s. Each type has `notify.route.<type>` with the value `monolith` (default) or `service`. It is read by `enqueue_notification` at insert time.
- **Route**: a `route` column on `notifications`, `monolith` or `service`. It is set once, when the row is created, from the type's flag, and never changes. Existing rows default to `monolith`. The old worker takes only `monolith` rows; the outbox relay takes only `service` rows.
- **Outbox relay**: a loop in the monolith, on every instance, that reads `service`-routed rows still `pending` and publishes them to the broker. It is used because the broker cannot join the database transaction, so publishing inside the caller's transaction is not possible.
- **Deliveries**: the service's own table, one row per notification, keyed by notification id. Columns: id, type, email, payload, created_at (the monolith's enqueue time, taken from the message), sent_at (set when MailRelay accepts), status (`pending`, `sent`, `failed`), attempts, next_attempt_at.
- **Message**: carries everything needed to send, so the service never calls back to the monolith: id, type, user email, payload, created time.

## Fixed rules

- Callers of `enqueue_notification(tx, ...)` do not change. The `notifications` table stays the first place a notification is recorded.
- The monolith and the service never read or write each other's database. The broker is the only link.
- Every send passes the notification id as MailRelay's `idempotency_key`.
- Retry policy, on either side: 5 attempts, waits of 1, 2, 4 and 8 minutes before attempts 2 to 5, then mark `failed` and page on-call. (All waits together are 15 minutes, inside MailRelay's 24-hour key memory.)
- Rendering moves into the service.
- Move one type at a time: `shipping_update`, then `order_confirmed`, then `password_reset`. Each runs on the service for at least 3 days before the next moves.
- `password_reset` has a requirement of p99 enqueue-to-MailRelay under 60 s. It moves only after the service has shown that on `order_confirmed`.
- Rollback of a type is a flag flip back to `monolith`, effective within a minute, losing and re-sending nothing in flight.
- Nothing lost, nothing duplicated: every notification whose enqueuing transaction committed ends up accepted by MailRelay or marked `failed` with on-call paged, and no user gets one twice, including during cutover and rollback.

## Steps, in shipping order

1. **Idempotency keys on the old worker.** Starts on every send. Pass `row.id` as `idempotency_key` in `_deliver`. State: none new. Why first: it ends the roughly 30 duplicate emails a week (a crash after MailRelay accepts but before the batch commit resends the row), and it protects any resend during cutover or rollback. If MailRelay fails, the existing retry code handles it.
2. **Routing.** Add the `route` column. Make `enqueue_notification` read the type's flag and set `route` in the same insert, inside the caller's transaction. Change the old worker's query to take only `route = 'monolith'` rows. Flags start at `monolith`, so nothing changes yet. Because route is fixed at insert, a flag flip affects only new rows.
3. **Build the Notification Service**, with its own database and `deliveries` table, deployed but receiving nothing.
   - Consumer: starts on each message. It inserts a `pending` `deliveries` row keyed by id, skipping the insert if the id exists, then acknowledges. A crash before the acknowledgement causes a redelivery, which the existing id makes harmless. If the insert fails (for example the service database is down), it does not acknowledge, and the broker redelivers after 30 s.
   - Sender: starts every second. It picks due `pending` rows one at a time with a row lock (`FOR UPDATE SKIP LOCKED`), renders the template, sends with the id as `idempotency_key`, and commits per row. Other instances skip a locked row and take the next. On success it sets `sent` and `sent_at`. On a MailRelay error (including timeout) it increases `attempts` and sets `next_attempt_at` by the backoff, or at attempt 5 sets `failed` and pages on-call. State lives in `deliveries`. The MailRelay call has a client timeout, so a hung call ends as an ordinary error and releases the lock.
   - A crash after MailRelay accepts but before the commit leaves the row `pending`. The resend carries the same key, and MailRelay drops it.
   - Templates: the service gets its own copy of the templates for the three types. The monolith keeps its copy for rollback until step 8. Until then, a template change is made in both places by hand.
4. **Outbox relay in the monolith.** Starts every second (the 60 s requirement leaves room), on every monolith instance. A `service`-routed row starts `pending`. Each loop, an instance locks a few rows with `route = 'service' AND status = 'pending'` using `FOR UPDATE SKIP LOCKED`, so two instances never take the same row. It publishes each with its full message, waits for the broker's confirmation, sets `status = 'handed_off'` and commits. The monolith row records only the handoff; the final outcome (`sent` or `failed`) lives in the service. If the broker is down, no confirmation arrives, the row stays `pending`, and the relay retries on the next loop. A crash after publishing but before the commit causes a second publish, which the service ignores by id.
5. **Move `shipping_update`.** Flip `notify.route.shipping_update` to `service`. Watch relay backlog, `failed` counts and latency for at least 3 days.
6. **Move `order_confirmed`** after those 3 days. Watch the same things for at least 3 days, and record the service's p99 enqueue-to-MailRelay latency, measured as `sent_at - created_at` in `deliveries`.
7. **Move `password_reset`** only if that p99 was under 60 s. Run it for 7 days.
8. **Remove the old worker** after `password_reset` has run on the service for 7 days. Until then it stays deployable.

## Rollback

Flip the type's flag back to `monolith`. New rows take effect within about 10 s and are sent by the old worker. Rows already routed to `service`, including ones in the broker, are finished by the service, so keep the service running during rollback. No row is on both paths, because route is fixed per row. Every send carries the same key, so even a mistaken second send within 24 hours is dropped by MailRelay.

## Failures

| Failure | Result |
|---|---|
| Monolith crash before commit | No row exists, so nothing is sent (as today). |
| Broker down | Rows wait `pending` in the monolith; relay retries. |
| Relay crash after publish | Duplicate message; service ignores it by id. |
| Message redelivered | The service ignores it by id. |
| Service database down | Consumer does not acknowledge; broker redelivers after 30 s. |
| Service crash after send | Row still `pending`; resend is dropped by MailRelay's key. |
| MailRelay down or hanging | Call times out, retries per the policy, then `failed` and on-call paged. |
| Row marked `failed` | Nothing resends it automatically; on-call is paged and handles it by hand (as today). |

## Open questions

- The monolith row stops at `handed_off`; who needs to see the final status there, and should the service report it back over the broker?
- What the on-call runbook says to do with a `failed` notification is not known here, nor whether a manual resend after 24 hours needs a new key.
- The MailRelay client timeout value is not set; it must be well under 60 s.
- Latency uses `created_at` from the monolith clock and `sent_at` from the service clock; clock skew between them is not accounted for.

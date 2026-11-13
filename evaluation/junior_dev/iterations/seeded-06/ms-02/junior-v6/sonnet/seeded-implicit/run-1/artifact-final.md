# Plan: extract notifications into a Notification Service

## Summary

Today the monolith sends emails itself. Business code calls `enqueue_notification(tx, ...)` inside its own transaction, which inserts a `pending` row into the monolith's `notifications` table. A worker thread on every monolith instance polls that table every 5 seconds, renders the template, sends through MailRelay, and commits once per batch of 50. This competes with checkout for CPU and database connections. If an instance dies mid-batch, the rows already sent stay `pending` and are sent again. Support sees about 30 duplicate emails a week.

In the new design, `enqueue_notification` still writes the row in the caller's transaction, so the `notifications` table stays the first record. A relay in the monolith publishes new rows to the broker. A separately deployed Notification Service consumes them, renders them, sends them to MailRelay, and keeps its own retry state in its own database. Every send carries the notification id as MailRelay's idempotency key, so a repeated send is dropped and never reaches the user twice. One email type at a time moves to the service, chosen by a flag, so each move can be undone.

## Terms

- **Monolith**: the existing application. The old worker, `enqueue_notification` and the `notifications` table live there.
- **Notification Service**: the new, separately deployed service with its own database. It never touches the monolith's database, and the monolith never touches its database.
- **Broker**: the message queue already used by billing and search. It is the only channel between the monolith and the service. It is at-least-once: a message not acknowledged within 30 s is redelivered, possibly to another consumer. A publisher gets a confirmation once the broker has stored the message.
- **MailRelay**: the email provider. `send()` takes an optional `idempotency_key`. If MailRelay accepted a send with the same key in the last 24 hours, it drops the new one and returns success. Today we pass no key.
- **Idempotency key**: the notification's id (a UUID made when the row is inserted). Using the same key on every send of one notification is what prevents duplicates.
- **Flag**: `notify.route.<type>`, read with `flags.get(name)` in the monolith. A change reaches all monolith instances within 10 s. Default is off, meaning the monolith sends.
- **`route`**: a new column on `notifications`, either `monolith` or `service`. It says who owns the row. It is set once, when the row is inserted, and never changes.
- **`handed_off`**: a status in the monolith's `notifications` table. It means the broker confirmed it stored the message. The monolith is finished with that row.
- **Outbox**: the rows in `notifications` with `route = service` and status `pending`, not yet handed to the broker. The relay reads them.
- **Row lock**: `SELECT ... FOR UPDATE SKIP LOCKED`, as the old worker uses. One instance holds a row for the length of its transaction. Other instances skip it. If the holder dies, the database drops its connection and releases the lock.
- **`deliveries`**: the service's table, one row per notification, holding its status (`pending`, `sent` or `failed`), attempt count and next attempt time.
- **Types**: `shipping_update` (about 40,000 a day), `order_confirmed` (about 12,000 a day) and `password_reset` (about 1,500 a day, with a required p99 enqueue-to-MailRelay latency under 60 s). All three are email only.

## How it runs

1. **Enqueue (starts when business code calls `enqueue_notification`).** Inside the caller's transaction, it reads the flag for the type and inserts a `pending` row with `route = service` if the flag is on, otherwise `monolith`. If the caller's transaction rolls back, the row never exists, so nothing is sent. Callers do not change.
2. **Old worker (rows with `route = monolith`).** It works as today: 5 attempts, waits of 1, 2, 4 and 8 minutes, then mark `failed` and page on-call. The changes are that it selects only `route = monolith` rows and passes the row id as `idempotency_key`. If it crashes before the batch commit, it resends the row and MailRelay drops the repeat.
3. **Relay (a loop on every monolith instance, for rows with `route = service` and `status = pending`).** Every 1 second it opens a transaction and takes up to 50 such rows with the row lock, so two instances never take the same row at once. It publishes one message per row to `notifications.requested` and waits up to 10 s for the broker's confirmations. It sets only the confirmed rows to `handed_off` and commits. Rows with no confirmation stay `pending` and are taken again on the next pass; if the broker had stored one anyway, the service ignores the second copy. A crash before the commit also means the rows are published again and the service ignores the copies. If the broker is down, rows wait in the outbox and the relay retries on its next pass, so nothing is lost. The monolith never learns the outcome of the send. To see what happened to one notification, look up its id in the service's `deliveries` table.
4. **Service intake (starts when a message arrives).** The message holds `id`, `type`, `email`, `payload` and `created_at` (the enqueue time). The service inserts a `deliveries` row keyed by `id`, status `pending`, 0 attempts, due now. If the id already exists, it inserts nothing. Only after that local commit does it acknowledge the message. If it crashes before acknowledging, the broker redelivers and the insert finds the row already there. A redelivered message therefore never creates a second send.
5. **Service sender (a loop on every service instance).** Every 1 second it starts a pass. A pass takes due `pending` rows (next attempt time has passed) one at a time with the row lock, and keeps going until no row is due. Only then does it wait 1 second. A burst is drained in one long pass, and several instances share it. For each row it renders the template (rendering now lives in the service), then calls MailRelay with `idempotency_key` = the id and a 10-second timeout, which keeps the lock short. It marks the row `sent` and commits after each row, not each batch. If an instance dies while holding the lock, the lock is released, the row is still `pending` and due, and another instance picks it up. If it crashes after MailRelay accepted but before the commit, the row is sent again with the same key and MailRelay drops it. This holds because the longest retry span is 15 minutes, inside MailRelay's 24-hour window.
6. **Retries (in the service, for any MailRelay error or timeout).** Same policy as today, kept in the `deliveries` row. Each failure adds 1 to the attempts. After attempts 1 to 4 the row stays `pending` and its next attempt time is set 1, 2, 4 and 8 minutes ahead; the sender skips it until then. After the 5th failed attempt it marks the row `failed` and pages on-call. If MailRelay is down, rows wait and retry on this schedule.
7. **Metrics.** The service reports p99 latency (sent time minus `created_at`) per type, and failed counts. The latency includes the relay poll, the broker hop and the sender poll, so the 60 s target for `password_reset` covers them. The monolith reports relay backlog: the number of `route = service` rows still `pending`.

## What happens when things fail

| What fails | What happens |
|---|---|
| Caller's transaction rolls back | No row, no notification. |
| Monolith instance dies mid-batch (old worker) | Rows are resent with the same key. MailRelay drops the repeats. |
| Broker down | Rows stay `pending` in the outbox. The relay retries. |
| Broker confirms only some of a batch, or confirmation times out | Confirmed rows become `handed_off`. The rest stay `pending` and are published again on the next pass. The service ignores any copy it already has. |
| Relay dies before commit | Rows are published again. The service ignores the copies. |
| Message redelivered | The `deliveries` insert finds the id and does nothing. |
| Service dies before acknowledging | The broker redelivers after 30 s. The insert finds the id or creates it. |
| Service dies mid-send (holding the row lock) | The lock is released. Another instance picks the row up. |
| Service dies after MailRelay accepted | Resent with the same key. MailRelay drops it. |
| MailRelay down or slow | Retries on 1, 2, 4, 8 minutes. After 5 attempts: `failed` and on-call paged. |

## Rollout order

1. Pass the notification id as `idempotency_key` in the old worker. This ships alone, and it already stops the weekly duplicates.
2. Add the `route` column (default `monolith`). Change the old worker to select only `route = monolith`. Make `enqueue_notification` read the flags. All flags are off, so nothing changes yet.
3. Build and deploy the Notification Service with its database, consumer, sender, templates and metrics. It receives no traffic yet.
4. Deploy the relay in the monolith.
5. Turn on `shipping_update`. It moves first because it has no latency requirement, and its volume tests the service. Run at least 3 days.
6. Turn on `order_confirmed`. Run at least 3 days.
7. Turn on `password_reset`, only after the service has shown p99 enqueue-to-MailRelay latency under 60 s on `order_confirmed`. It moves last because it is the only type with a latency requirement, so it moves only once the service has proven it can meet it. Watch relay backlog, failed counts and latency during each move.
8. After `password_reset` has run on the service for 7 days, remove the old worker. Until then it stays deployable.

## Rollback

Flip the type's flag off. It takes effect within 10 s (the required limit is one minute). New notifications then get `route = monolith` and go to the old worker. Rows already marked `service` stay with the service, which finishes them. No row changes owner, so none is lost and none is sent by both sides. Even a manual handoff would be safe, because both sides use the same idempotency key.

## Open questions

- If the service itself is broken, rollback does not rescue rows already marked `service`. They wait until the service recovers. Decide if that is acceptable.
- Where the metrics are stored and graphed is not specified.
- The monolith's current MailRelay timeout is not in the files. The service uses 10 s by choice.

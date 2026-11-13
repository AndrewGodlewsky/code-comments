# Plan: move notification sending into the Notification Service

## The finished flow

```
business transaction ── enqueue_notification ──▶ monolith DB: notifications
                                                   (route, status)
        │  outbox relay (inside the monolith, polls every 1 s):
        │  publish, wait for broker confirmation, mark row "published"
        ▼
broker topic: notifications.requested
  (at-least-once; a message not acked within 30 s is redelivered,
   possibly to another consumer instance)
        │  consumer (inside the service): insert row, commit, then ack
        ▼
service DB: deliveries (status, attempts, next_attempt_at)
        │  sender (inside the service, polls every 1 s):
        │  render, send, record the result
        ▼
MailRelay (idempotency_key = notification id; a repeat within 24 h is dropped and reported as success)
```

**Message on `notifications.requested`:** `notification_id`, `type`, `email`, `payload`, `created_at`. It carries everything the service needs to render and send the email, because the service cannot read the monolith's database. The service does the template rendering.

**Where state lives**

| State | Lives in | Written by |
|---|---|---|
| The notification, its `route`, and whether it has been handed off (`pending` → `published`) | monolith `notifications` table | `enqueue_notification`, outbox relay |
| Send state on the old path (`pending` → `sent` / `failed`, attempts) | monolith `notifications` table | old worker (only `route = 'monolith'` rows) |
| Messages in transit | broker | outbox relay |
| Send state on the service (`status`, `attempts`, `next_attempt_at`) | service `deliveries` table, primary key `notification_id` | consumer, sender |
| Which side each type is routed to | monolith flag `notify.route.<type>` | operator |

**Two rules that make it safe**

- *One sender per notification.* `route` is written once, at enqueue, and never changes. The old worker only takes `route = 'monolith'` rows and the relay only takes `route = 'service'` rows.
- *Every hop retries, and every repeat is harmless.* The relay and the broker may deliver a message more than once. The `deliveries` primary key absorbs repeats before sending, and MailRelay's idempotency key absorbs repeats at sending.

The first durable record is still the monolith row that `enqueue_notification` inserts inside the business transaction. It exists only if that transaction commits. Its `id` (a UUID generated at enqueue) is the `notification_id` used everywhere after.

## Steps

### 1. Make the old worker idempotent
- **Starts:** first deploy, before anything else.
- **Change:** `_deliver` passes `idempotency_key=row.id` to `mailrelay.send`.
- **Failure:** suppose an instance dies after MailRelay accepted part of a batch but before the batch commit. Those rows stay `pending`, and the next pass re-sends them with the same key. MailRelay drops the repeats and returns success, so the rows become `sent`. This removes today's ~30 duplicates a week.

### 2. Stamp a route on every notification
- **Starts:** after step 1 is live.
- **Change:** add the column `notifications.route` (`'monolith'` | `'service'`, default `'monolith'`). `enqueue_notification` reads `flags.get("notify.route." + ntype)` inside the caller's transaction and writes the value to `route`. The old worker's query adds `AND route = 'monolith'`.
- **State:** every flag starts at `monolith`, so behaviour does not change yet.
- **Failure:** if the flag read fails, write `monolith` (the old path stays deployable until step 8). A flag change takes up to 10 s to reach every instance. Rows enqueued in that window may get either route, but each row still has exactly one.

### 3. Build and deploy the Notification Service (it receives nothing yet)
- **Starts:** after step 2 is live.
- **Its database:** table `deliveries` with `notification_id` (primary key), `type`, `email`, `payload`, `status` (`pending` | `sent` | `failed`), `attempts`, `next_attempt_at`, `created_at`. The templates move here.
- **Consumer (runs for each broker message):**
  1. `INSERT ... ON CONFLICT (notification_id) DO NOTHING` with `status = 'pending'`, `attempts = 0`, `next_attempt_at = now()`.
  2. Commit.
  3. Ack the message. The ack comes after the commit and before any send.
  - Crash before the commit: no ack is sent, the broker redelivers after 30 s, and the insert happens then.
  - Crash after the commit but before the ack: the message is redelivered, the insert is a no-op, and the consumer acks.
  - Duplicate message (a redelivery or a relay republish): the insert is a no-op, the consumer acks, and nothing is sent again.
- **Sender (polls every 1 s):** takes up to 50 rows with `status = 'pending' AND next_attempt_at <= now()` using `FOR UPDATE SKIP LOCKED`. For each row it renders the email, calls `mailrelay.send(..., idempotency_key=notification_id)`, and commits that row's result on its own.
  - Success: the row becomes `sent`.
  - Error or timeout: `attempts + 1`. Below 5 attempts, `next_attempt_at` becomes now + 1, 2, 4 or 8 minutes (5 attempts in total). On the 5th failure the row becomes `failed` and on-call is paged.
  - Crash after MailRelay accepted the send but before the commit: the row is still `pending` and is re-sent on the next pass. MailRelay drops the repeat and returns success, so the row becomes `sent` and the user gets one email.

### 4. Add the outbox relay to the monolith
- **Starts:** after step 3 is live. While every flag is `monolith`, it finds nothing to do.
- **Loop (every 1 s), in one transaction:** select up to 100 rows with `route = 'service' AND status = 'pending'` (`FOR UPDATE SKIP LOCKED`), publish each as a message, wait for the broker's publish confirmation, set the row to `published`, and commit.
- **Failure:** if the broker is down or gives no confirmation, the rows stay `pending` and are retried on the next poll. An alert fires when the oldest such row is more than 60 s old. If the relay crashes after publishing but before the commit, the rows are published again and the consumer ignores the repeats.
- Once a row is `published`, the monolith is done with it. The relay never sends email and never retries sends.

### 5. Move `shipping_update`
- **Starts:** steps 1–4 are live, with dashboards for the relay backlog, the counts of pending and failed `deliveries`, and enqueue-to-MailRelay latency (`created_at` to `sent`).
- **Action:** set `notify.route.shipping_update = service`. Within 10 s, new rows get `route = 'service'`. Rows enqueued before the flip keep `route = 'monolith'`, and the old worker finishes them, including any retries.
- **Checks for 3 days:** each day, the number of service-routed rows in `notifications` equals the number of rows in `deliveries`, and the failed count is no higher than on the old path.
- **Rollback (the same for every type):** set the flag back to `monolith`. Rows enqueued after that go to the old worker. Rows already routed to the service are still relayed and sent by the service, because the relay and the service keep running. No row changes route, so nothing is lost or sent twice.

### 6. Move `order_confirmed`
- **Starts:** `shipping_update` has run on the service for 3 days and the checks pass.
- **Action and rollback:** as in step 5. Record the p99 latency for `order_confirmed` over its 3 days.

### 7. Move `password_reset`
- **Starts:** `order_confirmed` has run on the service for 3 days **and** its p99 latency is under 60 s. If it is not, fix latency first and do not flip.
- **Action and rollback:** as in step 5. Alert when p99 latency for `password_reset` reaches 60 s, and roll back if that limit is breached.

### 8. Remove the old path
- **Starts:** `password_reset` has run on the service for 7 days and no `route = 'monolith'` rows are still `pending`.
- **Change:** delete `run_worker`, make `enqueue_notification` always write `route = 'service'`, and drop the flags. The relay stays; it is now the only path.
- **Failure:** if monolith-routed rows are still pending, wait for the old worker to finish them before removing it.

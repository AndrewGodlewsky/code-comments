# Plan: extract notifications into a Notification Service

## How the pieces fit

Today, business code inserts a row into the monolith's `notifications` table inside its own transaction. A background worker on every monolith instance then sends the email through MailRelay (our email provider). After this plan, a new Notification Service sends the notification types we have moved, and the old worker keeps sending the rest.

- **`notifications` table (monolith database).** Still the first place a notification is recorded. Business code is unchanged and still calls `enqueue_notification(tx, ...)`.
- **`route` column (new, on that table).** Says who sends the row: `monolith` (the old worker) or `service`. It is set once, at enqueue time, from the flag `notify.route.<type>`, and never changes afterward. Every row has exactly one sender, so cutover and rollback cannot cause a double send.
- **Outbox relay (new, in the monolith).** A background thread that reads `service`-routed rows from the `notifications` table and publishes them to the broker topic `notifications.requested`. (The `notifications` table acts as an "outbox": the message is recorded in the same transaction as the business change, so it exists only if that transaction commits.)
- **Notification Service (new).** It has its own database with a `deliveries` table, a broker consumer, a sender, and the email templates. The service never touches the monolith's database, and the monolith never touches the service's. The broker is the only link between them. It delivers at least once: a message not acknowledged within 30 s is redelivered, possibly to a different consumer. A publisher gets a confirmation once the broker has stored the message.
- **MailRelay idempotency key.** If MailRelay has already accepted a send with the same `idempotency_key` in the last 24 hours, it drops the new send and returns success. We will pass the notification id as the key on every send. The longest retry sequence (waits of 1+2+4+8 min) takes 15 minutes, so a retry after a crash normally falls inside that window.

Three layers prevent duplicates:

1. The `route` column means exactly one side owns each notification.
2. The `deliveries` table uses the notification id as its primary key, so a message the broker redelivers is ignored.
3. The MailRelay idempotency key makes a re-send after a crash harmless.

## Steps, in shipping order

### 1. Pass the idempotency key from the old worker

- **Starts when:** immediately. It has no dependencies.
- **What moves:** `_deliver` calls `mailrelay.send(..., idempotency_key=row.id)`. No data moves.
- **State lives in:** the monolith `notifications` table, as today.
- **If something fails:**
  - If an instance dies after MailRelay accepts a send but before the batch commit, the rows stay `pending` and are sent again. MailRelay now drops that second send, which should remove the roughly 30 duplicate emails a week.
  - A MailRelay outage or timeout is handled by the existing retry policy. The retry reuses the same key, so a timeout that actually succeeded is not duplicated.

### 2. Add routing to the monolith (all flags off)

- **Starts when:** step 1 is deployed.
- **What moves:** a migration adds `notifications.route`, defaulting to `monolith`, so existing rows stay with the old worker. Two code changes follow.
  - `enqueue_notification` sets `route='service'` if `flags.get("notify.route.<type>")` is on, otherwise `monolith`. Its signature does not change. The flag is read inside the caller's transaction.
  - The worker query adds `AND route = 'monolith'`.
- **State lives in:** the monolith database for `route`. The flags live in the existing runtime flag system, and a change reaches every monolith instance within 10 s.
- **If something fails:** if an enqueue transaction rolls back, no row exists, as today. Before any flag is turned on, confirm every monolith instance is running the new worker query. An old instance ignores `route` and could pick up a `service` row.

### 3. Build and deploy the Notification Service (no traffic yet)

- **Starts when:** it can be built in parallel with steps 1 and 2. Deploy it before step 4.
- **What moves:** the service has four parts.
  - **Own database.** The `deliveries` table has these columns: `notification_id` (primary key), `type`, `email`, `payload`, `status` (`pending`, `sent` or `failed`), `attempts`, `next_attempt_at`, `created_at` (copied from the monolith row), and `sent_at`.
  - **Consumer.** For each message it runs `INSERT ... ON CONFLICT DO NOTHING` into `deliveries`, commits, and only then acknowledges the message. It does no sending, so it stays well inside the broker's 30 s acknowledgement window.
  - **Sender.** A loop selects due `pending` rows with `FOR UPDATE SKIP LOCKED`. For each row it renders the template, calls `mailrelay.send(..., idempotency_key=notification_id)`, and commits that row alone. It applies today's retry policy: 5 attempts, waits of 1/2/4/8 minutes, then `failed` plus a page to on-call. A MailRelay error, including a timeout, counts as a failed attempt.
  - **Templates.** Copied from the monolith. Until step 8 the old worker still renders its own copy, so keep the two copies identical.
- **State lives in:** the service database. The service records enqueue-to-MailRelay latency per type, using the `created_at` carried in the message.
- **If something fails:**
  - If the service crashes before committing the insert, the message was not acknowledged, so the broker redelivers it.
  - If it crashes after the commit but before acknowledging, the redelivery hits the primary key and is ignored.
  - If it crashes after MailRelay accepts a send but before the row is committed, the row is sent again with the same key and MailRelay drops it.
  - If MailRelay is down, rows retry on the policy until they are `failed` and on-call is paged.
  - If the service database is down, the consumer does not acknowledge, so messages wait in the broker.

### 4. Add the outbox relay and test end to end

- **Starts when:** steps 2 and 3 are live. No flag is on yet, so no real notification has `route='service'`.
- **What moves:**
  - A thread in the monolith polls every second for rows with `status='pending' AND route='service'`, using `FOR UPDATE SKIP LOCKED`.
  - It publishes each row to `notifications.requested`, carrying `id`, `type`, `email`, `payload` and `created_at`.
  - It waits for the broker's confirmation that the message is stored, then sets `status='handed_off'`.
  - The old worker never sees `handed_off` rows, because it selects only `status='pending'` rows with `route='monolith'`.
  - Smoke test: insert a few `route='service'` rows addressed to internal test mailboxes and confirm each arrives exactly once.
- **State lives in:** the monolith `notifications` table. The row stays `pending` until the broker confirms storage.
- **If something fails:**
  - If the broker is down, rows stay `pending` and the relay keeps retrying. Callers are unaffected, because enqueue only writes to the monolith database. An alert fires on relay backlog size and oldest row age.
  - If the relay crashes after publishing but before marking `handed_off`, it publishes the row again. The service ignores the duplicate by primary key.
  - The relay selects rows by their stored `route`, not by the current flag, so turning a flag off never strands a row that was already routed to the service.

### 5. Move `shipping_update` (40,000/day)

- **Starts when:** the step 4 smoke test passes. Turn on `notify.route.shipping_update`.
- **What moves:** new `shipping_update` rows get `route='service'` and flow through the relay, the broker, `deliveries`, and MailRelay. Rows enqueued before the flip stay with the old worker, which keeps running and finishes them. Nothing is re-routed, so nothing is sent twice.
- **State lives in:** the monolith row (`handed_off`) and the service `deliveries` row (`sent` or `failed`).
- **If something fails:** the failure cases are those of steps 3 and 4. Watch the metrics listed under "Rules that hold in every step". To undo the move, see "Rollback" below.
- **Hold:** at least 3 days before step 6.

### 6. Move `order_confirmed` (12,000/day)

- **Starts when:** `shipping_update` has run on the service for at least 3 days with no unresolved failures. Turn on `notify.route.order_confirmed`.
- **What moves and fails:** the same as step 5. This type also provides the latency evidence for step 7: record the p99 of enqueue-to-MailRelay time, meaning `sent_at` minus the monolith `created_at`.
- **Hold:** at least 3 days before step 7.

### 7. Move `password_reset` (1,500/day, p99 under 60 s required)

- **Starts when:**
  - `order_confirmed` has run on the service for at least 3 days, and
  - its measured p99 enqueue-to-MailRelay latency is under 60 s.

  Then turn on `notify.route.password_reset`.
- **What moves and fails:** the same as step 5. Also add alerts on p99 latency approaching 60 s and on the age of the oldest unsent `password_reset` row, in both the relay backlog and the service queue. If either alert fires and the delay does not clear quickly, roll `password_reset` back (see "Rollback").
- **Hold:** at least 7 days before step 8.

### 8. Remove the old worker

- **Starts when:** `password_reset` has run on the service for 7 days, and no `route='monolith'` row is still `pending`.
- **What moves:** delete `run_worker` and the monolith's rendering code. `enqueue_notification` then always sets `route='service'`. Remove the per-type flags.
- **State lives in:** the monolith `notifications` table, which remains the record of enqueues. Delivery state lives in the service.
- **If something fails:** rollback by flag is no longer possible after this step. That is why the old worker stays deployable through steps 1 to 7.

## Rules that hold in every step

- **Retries.** The policy is unchanged: 5 attempts, waits of 1/2/4/8 minutes, then `failed` and a page to on-call. The service's sender and the old worker each apply it to the rows they own.
- **Rollback.**
  1. Turn off `notify.route.<type>`. It takes effect on every monolith instance within 10 s, well inside one minute.
  2. New notifications of that type then route to the old worker.
  3. Notifications already routed to the service finish there. Keep the service and relay running until they have drained.
  4. Nothing is re-routed, so nothing is lost or re-sent.
  5. Only if the service must be abandoned before its rows drain: an operator may reset those rows to `route='monolith'` and `status='pending'`. Do this only within 24 hours of the row's first send, while MailRelay still remembers the key. Otherwise a row the service already sent could be sent again.
- **Nothing lost.** A committed enqueue always has a monolith row. The relay keeps republishing it until the broker confirms storage. The service keeps retrying it until MailRelay accepts it, or it is marked `failed` and on-call is paged.
- **Watch during every move.** Relay backlog size and oldest age, service `pending` depth, `failed` count, and p99 latency per type.

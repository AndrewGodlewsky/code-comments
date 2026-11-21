# Plan: extract notifications into a Notification Service

## Design in brief

- **Route is decided per row, at enqueue time.** `enqueue_notification` reads the flag `notifications.route.<type>` (`monolith` or `service`) and writes it into the row. Each notification has exactly one owner, so nothing is sent twice across the two systems, and a flag change only affects rows enqueued after it.
- **The monolith `notifications` table is the outbox.** Rows exist only if the caller's transaction committed. A publisher forwards `service`-routed rows to the broker.
- **The service writes an inbox before it acks.** A consumer inserts each message into the service's `deliveries` table with `ON CONFLICT DO NOTHING`, then acks. Sending runs from that table, not from the broker, so a retry backoff of up to 15 minutes never outlasts the 30 s ack window and never causes redelivery.
- **Every MailRelay send carries `idempotency_key = notification id`.** All retries fall inside the 24 h window, so a retry after a crash returns success instead of sending again.
- **Status flows back by broker event.** The monolith row is updated from those events so support tooling stays accurate. The service is the authority on whether a send happened.
- **Assumed:** PostgreSQL (the SQL uses `FOR UPDATE SKIP LOCKED` and `now()`). Broker retention is not stated in the brief and is an open item.

## Steps

### 1. Make the old worker idempotent (no routing yet)

- **Starts:** deploy of the monolith worker change.
- **Data moves:** none. Pass `row.id` as `idempotency_key` on every `mailrelay.send`. Commit after each row instead of once per batch. The row lock is still held during the send, as it is today.
- **State lives:** monolith `notifications` table, schema unchanged.
- **On failure:**
  - Crash after MailRelay accepts but before commit: the row stays `pending` and is resent with the same key. MailRelay drops it and returns success, so the row becomes `sent`. At most one row is exposed, not a whole batch of 50.
  - MailRelay down or timeout: today's retry policy applies unchanged.
  - Redelivery: not applicable (no broker yet).
- **Gate:** one week of support duplicate reports with the key in place, to confirm the ~30/week figure drops toward zero.

### 2. Add routing to the monolith schema and enqueue

- **Starts:** migration, then the worker deploy.
- **Migration:** add `route text not null default 'monolith'` and `published_at timestamptz null`. Add a partial index on `created_at WHERE route = 'service' AND published_at IS NULL`. Add an index on `(route, status, next_attempt_at)` for the old worker.
- **Worker change:** the old worker's query adds `AND route = 'monolith'`. Deploy this before any row can be routed to `service`.
- **Enqueue change:** write `route` from `flags.get('notifications.route.<type>')`. A missing or unrecognised value resolves to `monolith`.
- **Data moves:** none. All existing rows are `monolith`.
- **State lives:** monolith database and runtime flags.
- **On failure:** a flag store outage or bad value falls back to `monolith`. A failed migration changes nothing. Rolling back this step is safe because the column is inert while every flag is `monolith`.

### 3. Stand up the Notification Service with no traffic

- **Starts:** service deploy. The consumer subscribes to the notification topic, but no messages exist for it yet.
- **Message contract v1:** `{id, type, user_id, email, payload, enqueued_at, schema_version}`. `enqueued_at` is the monolith row's `created_at` from the database clock.
- **Service database, table `deliveries`:** `notification_id` (PK), `type`, `user_id`, `email`, `payload`, `enqueued_at`, `status` (`pending` | `sending` | `accepted` | `failed`), `attempts`, `first_attempt_at`, `next_attempt_at`, `lease_until`, `accepted_at`, `failed_at`, `last_error`, `page_sent_at`.
- **Consumer:** insert into `deliveries` with `ON CONFLICT DO NOTHING`, commit, then ack. A duplicate delivery is a no-op.
- **Sender loop, using short transactions:**
  1. Claim in a committed transaction: rows with `status = 'pending' AND next_attempt_at <= now()`, or `status = 'sending' AND lease_until < now()`. Use `FOR UPDATE SKIP LOCKED`. Set `status = 'sending'`, `attempts = attempts + 1`, `first_attempt_at` if null, and `lease_until = now() + 60 s`. The attempt is recorded before the network call.
  2. Guard: if `now() - first_attempt_at > 23 h`, do not send. Mark `failed` and page on-call, because MailRelay's 24 h dedupe window can no longer be relied on.
  3. Call MailRelay with `idempotency_key = notification_id` and a client timeout below the lease (about 20 s).
  4. On success, in one transaction: `status = 'accepted'`, `accepted_at = now()`, and write a status event to the service's own outbox.
  5. On error: if `attempts >= 5`, mark `failed`, write the status event, and page. Otherwise set `status = 'pending'` and `next_attempt_at = now() + BACKOFF[attempts - 1]`, where BACKOFF is 1, 2, 4, 8 minutes.
- **Pager:** pages are sent from a loop that picks up `failed` rows with `page_sent_at IS NULL`, then sets `page_sent_at`. A crash between the failure and the page results in a page on restart. Paging twice is acceptable; paging zero times is not.
- **Rendering:** not yet wired in (step 4).
- **State lives:** service database only. The monolith never connects to it.
- **On failure:** the service is inert until traffic arrives. A crash during claim leaves the row unchanged. A crash during a send leaves `sending` with an expired lease, so the next claim resends with the same key.

### 4. Move template rendering into the service and prove parity

- **Starts:** after step 3. Templates for all three types are copied into the service, and the sender renders before the send.
- **Data moves:** none in production. Recorded payloads from the last 30 days, covering all three types, are rendered by both renderers. Subjects and bodies must match byte for byte.
- **State lives:** templates in the service repo. The monolith keeps its renderer for `monolith`-routed rows.
- **On failure:**
  - A mismatch blocks cutover of that type.
  - Template edits during the transition must update both copies, or the type's cutover is paused.
  - A render error is treated as a send error, so the normal retry and page policy applies.

### 5. Add the monolith outbox publisher (inert until a flag flips)

- **Starts:** deploy on every monolith instance, as a background loop like today's worker.
- **Loop, every 1 s:**
  1. `BEGIN`
  2. `SELECT id, type, user_id, email, payload, created_at FROM notifications WHERE route = 'service' AND published_at IS NULL ORDER BY created_at LIMIT 50 FOR UPDATE SKIP LOCKED`
  3. Publish each message with key `id`, and wait for broker confirmation.
  4. `UPDATE notifications SET published_at = now()` for the confirmed rows.
  5. `COMMIT`
- **Data moves:** the message contract v1. Only rows committed by a caller are visible to the publisher, so rolled-back rows are never published.
- **State lives:** the monolith database is the outbox. The broker holds messages in transit.
- **On failure:**
  - Broker down: publish fails, the transaction rolls back, rows stay unpublished, and the loop retries with backoff. Alert when the oldest unpublished row is older than 60 s.
  - Crash after confirmation but before commit: rows are republished later. The service's inbox absorbs the duplicate.
  - No ordering is guaranteed across instances. No step relies on ordering across notifications.

### 6. Add status return and the republish sweeper

- **Status events:** on each terminal state, the service publishes an event from its own outbox to a `notification.status` topic. The monolith status consumer runs `UPDATE notifications SET status = $s, attempts = $a WHERE id = $id AND route = 'service' AND status = 'pending'`, then acks after commit.
- **Republish sweeper (monolith):** rows with `route = 'service' AND status = 'pending' AND published_at < now() - 2 h` are republished with the same key, and `published_at` is updated. The threshold must sit below broker retention, which is an open item. Republishing is safe because the service inbox dedupes. If the service never received the message, it sends once.
- **Starts:** deploy. No type is routed yet.
- **On failure:**
  - Status events lost: the sweeper republishes the notification, and the service re-emits the status for a terminal duplicate.
  - Consumer crash before ack: redelivery, and the conditional update is idempotent.
  - Broker retention shorter than the outage: the sweeper restores the message from the monolith row, so nothing is lost.

### 7. Cut over `shipping_update`

- **Starts:** set `notifications.route.shipping_update = service`. Instances see it within 10 s.
- **Data moves:** new `shipping_update` rows are routed to the service. Existing `pending` monolith rows of this type stay with the old worker and finish there. Nothing is moved.
- **State lives:** each row's `route` column records its owner. The service database holds delivery state.
- **Minimum duration:** 3 days.
- **Gate to move on:**
  - zero duplicate reports from support;
  - MailRelay accept audit matches the service's `accepted` count;
  - every `failed` row has a page;
  - outbox lag stays under 10 s at p99.
- **On failure:**
  - Service down: rows wait in the outbox and are sent when it recovers. Nothing is lost.
  - Broker down: as in step 5.
  - MailRelay down: retry policy, then `failed` plus page.
  - Crash mid-send: lease expires, resend with the same key.
  - Redelivery: inbox dedupe.
- **Rollback:** set the flag to `monolith`. New rows reach the monolith worker within about 10 s. Rows already routed to the service keep draining there. Nothing is re-sent or lost. The publisher, status consumer and sweeper keep running until all service-routed rows are terminal.

### 8. Cut over `order_confirmed` and measure latency

- **Starts:** after step 7's gate. Set `notifications.route.order_confirmed = service`.
- **Data moves and failure handling:** the same as step 7.
- **Latency measure:** `accepted_at - enqueued_at`, where `enqueued_at` is the monolith's `created_at`. The measure includes publisher lag, so it is conservative. Keep NTP in sync across hosts. Publisher poll interval is 1 s.
- **Minimum duration:** 3 days. At 12,000 per day, that is about 36,000 samples, enough for a stable p99.
- **Gate for step 9:** the service shows p99 under 60 s over this window, with the same criteria as step 7.

### 9. Cut over `password_reset`

- **Starts:** after step 8's gate. Set `notifications.route.password_reset = service`. This starts the 7-day decommission clock.
- **Data moves and failure handling:** as in step 7. Password reset is the latency-sensitive type, so a p99 breach during this window triggers rollback.
- **Rollback:** a flag flip to `monolith`, at any point in the 7 days. The old worker stays in the build and its thread stays started, so rollback needs no deploy.

### 10. Hold for 7 days

- **Watch:** duplicate reports, page count, `password_reset` p99, outbox lag, and sweeper republish count. The sweeper should report zero or near-zero.
- **State lives:** unchanged. Rollback remains a flag flip.

### 11. Decommission the old worker

- **Preconditions:**
  - `password_reset` has run on the service for at least 7 days;
  - zero `route = 'monolith' AND status = 'pending'` rows remain;
  - all three flags are `service`.
- **Remove:** the old worker thread, `run_worker` and `_deliver`, the monolith renderer, and the monolith branch of the route flag. Keep the publisher, status consumer and sweeper, because service-routed rows still need them. Keep the `route` column as the record of ownership.
- **On failure:** after removal, rollback is a redeploy of the previous build rather than a flag flip. Keep that build artifact for at least one week.

## Gates and invariants

- **No loss:** every committed notification either has a MailRelay acceptance or a `failed` row with a page. The outbox persists across monolith, broker and service outages. The sweeper covers broker retention loss.
- **No duplicates:** one owner per row via `route`. Every MailRelay send carries the notification id as its key. The service inbox dedupes on that id. The 23 h guard stops resends that fall outside the 24 h dedupe window.
- **Retries:** 5 attempts, backoff 1/2/4/8 minutes, then `failed` and page. The attempt is recorded before each send, so a crash cannot reset the count.
- **Timeline:** about 3 days for `shipping_update`, 3 days for `order_confirmed`, then `password_reset`, then 7 days before decommission.

## Open items

- **Broker retention:** not stated in the brief. The sweeper threshold of 2 h must sit below it.
- **MailRelay dedupe:** the brief says a key deduplicates for 24 h. Confirm the key is honoured on retries and that a deduplicated send returns success, as the overview describes.
- **Database engine:** assumed PostgreSQL. Confirm before writing the migration.
- **Clock sync:** the p99 gate depends on clocks that agree across the monolith database and service hosts.
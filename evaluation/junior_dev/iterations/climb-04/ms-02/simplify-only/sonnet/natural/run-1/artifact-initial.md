# Plan: extract notifications into a Notification Service

## Design in brief

These decisions apply to every step below.

- **Source of truth for intake.** `enqueue_notification(tx, ...)` keeps its signature and still inserts into the monolith's `notifications` table inside the caller's transaction. That is the only place a notification is created.
- **Ownership is per row.** A new column `notifications.owner` ('monolith' or 'service') is stamped at enqueue time. It is read from the per-type flag `notifications.via_service.<type>` through `flags.get`. Each row has exactly one sender for its whole life. The flag only decides the owner of future rows, so a flag flip cannot move a row that is already in flight.
- **Hand-off uses an outbox.** A relay in the monolith publishes service-owned rows to the broker. It marks `published_at` only after the broker's storage confirmation.
- **Service side.** The service has its own database with these tables:
  - `inbox`: the notification id is the primary key, so it also acts as the dedup table. It also holds the retry state (`status`, `attempts`, `next_attempt_at`).
  - `result_outbox`: result events waiting to be published.
- **Result events.** The service publishes `sent` and `failed` events back over the broker. A monolith consumer applies them to `notifications.status`.
- **Duplicate protection has three layers:**
  1. Inbox primary key on the id, which absorbs redelivery and relay republish.
  2. `idempotency_key = notification id` on every MailRelay send, which absorbs a crash between MailRelay accepting and the local commit. MailRelay remembers keys for 24 hours. The longest retry window is 15 minutes, and crash recovery takes seconds to minutes, so this is well inside the window.
  3. Exclusive row ownership, which means the monolith never sends a service-owned row.
- **Retries.** These match today's policy exactly: 5 attempts, waits of 1, 2, 4 and 8 minutes before attempts 2 to 5, then `failed` and a page to on-call. The same constants and logic run in the service. The attempts counter increments only after a send returns a MailRelay error, as it does today.

## Step 1. Send the idempotency key from the old worker

- **Starts when:** this is the first change shipped. It needs no other work.
- **Change:** `_deliver` calls `mailrelay.send(..., idempotency_key=row.id)`. Nothing else in the worker changes.
- **Data and state:** no new data. The key is the existing `notifications.id`.
- **Failures:**
  - Instance dies after MailRelay accepted some of a batch but before the batch commit. The rows stay `pending` and are re-sent with the same key. MailRelay drops them and returns success, so the row is marked `sent` without a second email.
  - MailRelay times out after accepting. The retry returns success.
- **Gate to continue:** the duplicate-email count from support stays near zero for at least a week (it is about 30 a week today). Rows already re-sent before this shipped are not covered.

## Step 2. Prepare the monolith schema, ownership stamp and worker filter

- **Starts when:** Step 1 is verified.
- **Migration:** add `notifications.owner` (default `'monolith'`) and `notifications.published_at` (null).
- **Worker change:** `run_worker` adds `AND owner = 'monolith'` to its query.
- **Enqueue change:** `enqueue_notification` reads the type's flag and writes `owner`. All flags are off, so every row is `'monolith'`.
- **Gate before any flag is turned on:** confirm that every monolith instance runs the filtered worker. An old-code worker has no owner filter and would grab service-owned rows.
- **State:** the monolith database only.
- **Failures:**
  - The flag read fails or is missing. Default to `'monolith'`.
  - Instances disagree on the flag for up to 10 s after a flip. Each row is still stamped once, so there is no duplication.

## Step 3. Build and deploy the Notification Service in dark mode

- **Starts when:** it can run in parallel with Step 2. Nothing is published to it until Step 6.
- **Components:**
  - Its own database (`inbox`, `result_outbox`).
  - A broker consumer.
  - A sender worker.
  - A result publisher.
  - Template rendering, moved from `templates.render`.
  - Paging through `alerts`.
- **Consumer, per message:**
  1. In one service-DB transaction, `INSERT INTO inbox (id, type, email, payload, created_at, status='pending', attempts=0, next_attempt_at=now()) ON CONFLICT (id) DO NOTHING`.
  2. Commit.
  3. Acknowledge the message.

  Acknowledging only after the commit means a crash before the ack causes a redelivery, which hits the conflict and is simply acknowledged. The 30 s redelivery to a different consumer is handled the same way.
- **Sender worker:**
  1. Claim one due row with `FOR UPDATE SKIP LOCKED`.
  2. Render the template.
  3. Send with `idempotency_key=id`.
  4. In the same transaction, update `sent`, or the retry state, or `failed`. On `sent` and on `failed`, also write a `result_outbox` row.

  This commits per row, not per batch.
- **Failed rows:** a `failed` row also records "page owed". The page is sent after the commit and then cleared. A crash can cause a second page, never a missing one. The page is keyed by the id.
- **Result publisher:** it publishes `result_outbox` rows and marks them after the broker confirms. It is at-least-once.
- **Poison messages:** a message that fails processing after N redeliveries goes to a dead-letter queue and pages on-call, so it is never silently dropped.
- **Failures:**
  - Service crash mid-send. The row lock is released, the row is still `pending`, and another instance re-sends with the same key.
  - MailRelay down. Each attempt fails and follows the 1/2/4/8 minute backoff. After attempt 5 the row is `failed` and on-call is paged. This is unchanged from today.
  - Broker down. The consumer reconnects, and unacknowledged messages are redelivered.

## Step 4. Deploy the monolith relay and result consumer, still inert

- **Starts when:** Steps 2 and 3 are deployed.
- **Relay:**
  - Runs in the monolith and polls every 1 s.
  - Selects rows with `owner='service' AND published_at IS NULL` using `FOR UPDATE SKIP LOCKED`.
  - Publishes `{id, type, user_id, email, payload, created_at}` and waits for the broker confirmation.
  - Then sets `published_at`.
- **Result consumer:**
  - Applies `UPDATE notifications SET status=..., attempts=... WHERE id=? AND status='pending'`.
  - Acknowledges after commit. This is idempotent.
- **State:**
  - The monolith table holds the intake record, the publish marker and the final status.
  - The service database holds the retry state.
- **Failures:**
  - Relay crashes between broker confirmation and `published_at`. The row is republished, and the service inbox dedups it.
  - Broker down. Rows stay unpublished and the relay backs off and retries. Nothing is lost, because the row is in the committed monolith table.
- **Alerts added:**
  - The oldest unpublished service-owned row is older than 30 s.
  - A published row has had no result for 30 minutes.

## Step 5. Rehearse failures and rollback with a synthetic type

- **Starts when:** Step 4 is deployed.
- **Method:** use a test-only notification type addressed to internal mailboxes, with its own flag.
- **Drills to run:**
  - Kill the service mid-send.
  - Kill the relay mid-publish.
  - Force broker redelivery.
  - Take MailRelay down for more than 15 minutes, and confirm the row ends `failed` with a page.
  - Take the broker down.
  - Flip the flag back and forth under load.
- **Pass condition:** each notification produces exactly one email and one final status.
- **State:** the synthetic rows are in both databases.

## Step 6. Move `shipping_update` (40,000/day)

- **Starts when:** Step 5 passes. Turn on `notifications.via_service.shipping_update`. It takes effect on all instances within 10 s.
- **Data moved:**
  - New rows get `owner='service'`.
  - The relay publishes them, and the service sends them.
  - Rows stamped `'monolith'` before the flip drain on the old worker.
- **State:** as in the design above.
- **Failures:** as in Steps 3 and 4. Redelivery, relay replay and service crashes are all absorbed by the inbox and the key.
- **Soak:** at least 3 days. Watch:
  - Duplicate complaints.
  - Rows with no result.
  - Dead-letter depth.
  - Unpublished age.
  - Enqueue-to-MailRelay latency.
- **Rollback (flag flip, effective within about 10 s):**
  1. Turn the flag off.
  2. New rows are stamped `'monolith'` and sent by the old worker.
  3. Rows already stamped `'service'` stay with the service until they finish. The old worker's filter never touches them, so there is no re-send.
  4. The relay keeps publishing them, and the result consumer keeps updating their status. Keep both running during a rollback.

  The cost of this design is that if the service itself is down, in-flight service-owned rows wait for it to recover. They are not lost, and the alerts above fire.

## Step 7. Move `order_confirmed` (12,000/day)

- **Starts when:** `shipping_update` has run on the service for at least 3 days and is clean. Turn on `notifications.via_service.order_confirmed`.
- **Data, state and failures:** the same as Step 6.
- **Latency measurement:**
  - Measure p99 of `accepted_at - created_at`. `created_at` is carried in the message. `accepted_at` is the time MailRelay accepted the send, taken from the service and returned in the result event.
  - Both clocks must be on NTP. Alarm if skew is above 1 s.
  - The metric covers all notifications, including retried ones. A MailRelay failure rate above about 1% would therefore breach 60 s. Today's policy has the same property.
- **Soak:** at least 3 days. Rollback is the same flag flip as in Step 6.

## Step 8. Move `password_reset` (1,500/day, p99 under 60 s)

- **Starts when:** both conditions hold.
  - `order_confirmed` has run on the service for at least 3 days.
  - The service's p99 enqueue-to-MailRelay latency on `order_confirmed` was under 60 s over that period.

  Then turn on `notifications.via_service.password_reset`.
- **Added protection:**
  - A tighter alert for this type when the oldest unpublished row is older than 20 s.
  - A dedicated p99 dashboard and alarm at 45 s.
- **Failures:**
  - Broker outage. Reset emails queue in the table and go out when the broker recovers. The alarm fires, and on-call decides. The row is not moved back to the monolith, because that could duplicate the email.
  - MailRelay or service failure. The same retry policy applies.
- **Rollback:** the same flag flip, with the same drain semantics.

## Step 9. Decommission the old worker

- **Starts when:** `password_reset` has run on the service for 7 days, and all three flags have been on throughout.
- **Check first:** there are no `owner='monolith'` rows with `status='pending'`.
- **Until then:** the old worker stays deployed and idle. It is the rollback path.
- **Change:**
  - Remove `run_worker`, `_deliver` and the worker filter.
  - Hard-code `owner='service'` in `enqueue_notification` and remove the flags.
  - Keep the relay and the result consumer.
- **After this point:** rollback means redeploying the previous version. Per-type rollback by flag no longer exists.
- **Failures:** the same as for the running service.

## Open risks

- **Rollback when the service is down.** In-flight rows wait for the service. The design avoids a re-send by not reclaiming them. The 24-hour idempotency window makes reclaiming unsafe if the service recovers late.
- **Clock skew.** It can distort the latency metric, so it is monitored.

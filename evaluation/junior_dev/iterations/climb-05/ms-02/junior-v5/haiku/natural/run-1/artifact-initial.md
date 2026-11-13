# Plan: Extract notifications into a Notification Service

## Design in brief

Four decisions carry the rest of the plan.

1. **Each row has one route, fixed at insert.** `enqueue_notification` writes `route = 'service'` or `route = 'monolith'` into the `notifications` row, using the flag `notify.route.<type>`. Exactly one executor drains each route: the old worker drains `monolith` rows and the outbox relay drains `service` rows. No row changes route afterward. A flag flip therefore affects only new rows, and rows already in flight finish where they started. This is what makes rollback neither lose nor re-send.
2. **Duplicates are blocked in two layers.** Every MailRelay send carries `idempotency_key = notification.id`, which covers the 24-hour window. The service also keeps a durable `jobs` table keyed by notification id, so broker redelivery is a no-op. The MailRelay key alone is not enough, because its window is only 24 hours and broker dedupe must be permanent within its retention.
3. **The broker carries two topics.** `notifications.requested` goes from the monolith outbox to the service. `notification.status` goes from the service outbox back to the monolith, which updates its own `notifications` row. The monolith table stays the system record, and reconciliation can run against it.
4. **Retries stay in the sender, not the broker.** The consumer acknowledges a message only after its job row is committed. Retry timing comes from the job's `next_attempt_at`, so the broker's 30-second redelivery never counts as an attempt.

## Schema changes

Monolith `notifications` table:
- `route text not null default 'monolith'` (existing rows are all monolith)
- `published_at timestamptz null` (set when the outbox relay gets broker confirmation)
- Partial indexes on `(route, status)` for the old worker and the relay.

Notification Service database (new, owned only by the service):
- `jobs(notification_id pk, type, email, payload, enqueued_at, status [pending|sending|sent|failed], attempts, next_attempt_at, lease_until, last_error)`
- `events_outbox(id, notification_id, status, attempts, created_at, published_at)`
- Terminal rows are kept at least 30 days. This is longer than any redelivery or republish delay, which is seconds.

## Steps in shipping order

### 1. Send with the idempotency key on the old worker

- **Starts:** a normal release of the monolith.
- **Data moves:** none. `_deliver` passes `idempotency_key=str(row.id)` to `mailrelay.send`.
- **State:** unchanged monolith `notifications` table.
- **Also in this step (recommended):** commit per row instead of per batch. The per-batch commit is the cause of the known duplicate emails. The key alone turns those duplicates into MailRelay drops within 24 hours, but a row committed before the crash still avoids re-attempts.
- **Failure:**
  - Crash mid-batch: rows sent but uncommitted stay `pending`. The next run re-sends with the same key, and MailRelay drops the duplicate.
  - MailRelay down: existing retry policy, unchanged.
  - Rollback: revert the release. Keys sent during the change are harmless.

### 2. Add the route column and route-aware enqueue, all routes set to monolith

- **Starts:** a release containing the migration. The migration adds `route` and `published_at`.
- **Data moves:** none. `enqueue_notification(tx, user, ntype, payload)` keeps its signature. It reads `flags.get("notify.route.<ntype>")` and sets `route`. Missing or any value other than `service` yields `monolith`.
- **State:** monolith `notifications` table. Flags in the monolith.
- **Old worker change:** its select adds `AND route = 'monolith'`, so it never takes service rows.
- **Failure:**
  - Migration fails: nothing deployed.
  - Flag service unavailable: `flags.get` falls back to `monolith`, which is the safe default.
  - Old worker running an older build during rollout: it selects all pending rows, which is harmless because no rows are routed to `service` yet.

### 3. Add the outbox relay and the status consumer to the monolith, both inert

- **Starts:** a release. The relay has no rows to publish because every row is still `monolith`.
- **Data moves (when active):**
  - Relay: selects `route='service' AND published_at IS NULL AND status='pending'` with `FOR UPDATE SKIP LOCKED`, publishes `{id, type, email, payload, created_at}` to `notifications.requested` with the notification id as the message key, waits for broker confirmation, then sets `published_at`.
  - Status consumer: reads `notification.status`, runs `UPDATE notifications SET status=%s, attempts=%s WHERE id=%s AND route='service' AND status='pending'`. Repeated events are harmless.
- **State:** monolith table only.
- **Failure:**
  - Publish succeeds but `published_at` update fails: the relay republishes. The service's `jobs` primary key makes it a no-op.
  - Broker down: rows stay unpublished. They are delayed, not lost. The sweeper in this step pages if a `service` row is unpublished for more than 5 minutes.
  - Relay instances race: `SKIP LOCKED` prevents two instances from claiming the same row.

### 4. Build and deploy the Notification Service, receiving no traffic

- **Starts:** a service repository and deployment, separate from the monolith. The service has its own database and credentials. Nothing in the monolith reads or writes that database.
- **Data moves:** none yet. The service has a consumer on `notifications.requested`, a sender, the templates moved from the monolith, and an events outbox.
- **Consumer behavior:** in one transaction, `INSERT INTO jobs ... ON CONFLICT (notification_id) DO NOTHING`. Acknowledge the broker message only after the commit.
- **Sender behavior:**
  - Claim pending jobs with `next_attempt_at <= now()` and expired or null `lease_until`, using `FOR UPDATE SKIP LOCKED`, and set a lease longer than the MailRelay timeout plus margin.
  - Render the template, then call `mailrelay.send(..., idempotency_key=notification_id)`.
  - On success, mark `sent` and write a `sent` event to the outbox in the same transaction.
  - On `mailrelay.Error`, increment `attempts`. If `attempts >= 5`, mark `failed`, write a `failed` event, and page on-call. Otherwise set `next_attempt_at = now() + [1, 2, 4, 8][attempts-1]` minutes.
  - Lease expiry does not count as an attempt. Alert on lease expiries so a crash loop is visible.
- **Events outbox:** a loop publishes `notification.status`. The row is deleted or marked only after broker confirmation.
- **Rendering check:** golden tests compare monolith and service output for sample payloads of all three types. Byte-equal or a reviewed diff is required before cutover.
- **Failure:**
  - Service crash after commit, before ack: redelivery hits the primary key and is acknowledged.
  - Service crash mid-send: the lease expires and a new claim re-sends with the same key. MailRelay drops it if it was already accepted.
  - MailRelay timeout where the send actually succeeded: the retry with the same key is dropped by MailRelay.
  - MailRelay down: jobs retry on the backoff schedule and fail after 5 attempts with a page.
  - Broker down: the consumer stops. Monolith rows wait in the monolith table. The monolith relay retries. Nothing is lost.
  - Templates diverge from the monolith: prevented by the golden tests.

### 5. Verify the service end to end, and rehearse rollback

- **Starts:** a manual operator run after step 4 is deployed.
- **Data moves:** a small number of test notifications, created with `route='service'` for a non-customer test address, in the production environment. Use a test user, not a real type. Repeat the test with the MailRelay sandbox, if one exists, in staging.
- **Checks:**
  - Each test notification ends `sent` in the monolith table via the status event.
  - Kill the service mid-run and confirm there is no duplicate in MailRelay logs.
  - Flip `notify.route.shipping_update` to `service` in staging, then back. Confirm new rows follow the flag within 10 seconds, and that rows already on the service complete without re-send.
- **Failure:** any duplicate or missing status blocks step 6.

### 6. Cut over `shipping_update` (at least 3 days)

- **Starts:** an operator sets `notify.route.shipping_update = service`. Only after step 5 passes.
- **Data moves:** new `shipping_update` rows get `route='service'` at enqueue. The relay publishes them. The service sends them. Existing `monolith` rows still drain through the old worker.
- **State:** in the monolith, rows are `route='service'` and have `published_at` set. In the service, the `jobs` table holds the sends.
- **Clock:** the 3-day period starts once monolith `route='monolith'` backlog for this type is zero.
- **Reconciliation, daily:** count `shipping_update` rows created in the monolith against service rows that reached `sent` or `failed`. Any mismatch past 1 hour pages.
- **Failure:**
  - Service down: the rows wait, unpublished or pending. Not lost.
  - Mismatch: pause by flipping the flag back. New rows go to the old worker. Rows already routed to the service remain there and finish.

### 7. Cut over `order_confirmed` (at least 3 days)

- **Starts:** an operator sets `notify.route.order_confirmed = service` after step 6 has run for 3 days with no reconciliation mismatch.
- **Data moves:** as in step 6, for `order_confirmed`.
- **Latency measurement:** the service records `sent_at - enqueued_at` for every job of this type. Track p99 over the 3-day window. NTP-synced clocks are required, because `enqueued_at` comes from the monolith. The service also logs its receive time, so skew can be checked directly.
- **Gate:** `password_reset` may move only if p99 is under 60 seconds over this window. If it is not, hold step 8 and investigate.
- **Failure:** same as step 6. A latency miss does not roll anything back. It holds the next cutover.

### 8. Cut over `password_reset` (7 days before decommission)

- **Starts:** an operator sets `notify.route.password_reset = service` after step 7 has met the latency gate.
- **Data moves:** as in step 6, for `password_reset`. This is the last type to move.
- **Clock:** the 7-day period starts at the flag flip. It can be longer than 3 days because it is also the decommission gate.
- **Failure:**
  - Rollback: flip `notify.route.password_reset = monolith`. New reset requests go to the old worker within 10 seconds. Rows already routed to the service finish there. Password reset is user-facing, so the on-call engineer watches the queue after the flip.

### 9. Decommission the old worker (after 7 days on `password_reset`)

- **Starts:** the 7-day period in step 8 has elapsed with no reconciliation mismatch. Check that there are zero `route='monolith' AND status='pending'` rows in the monolith.
- **Data moves:** none. The `notifications` table stays, because it is the record of every notification.
- **Actions:** remove the old worker and `run_worker`, remove the flag reads and the `route` default if no longer needed, and remove the `notify.route.*` flags.
- **Keep deployable until the gate passes:** the old worker stays deployable until step 9. Rollback in step 8 depends on it.
- **Failure:** if a monolith-route row appears after removal, the status is stuck `pending`, and the sweeper in step 3 pages. Restoring the worker is a revert of this step's release.

## Rollback procedure (applies to every type)

1. Set `notify.route.<type> = monolith`. Flag propagation is within 10 seconds, and the old worker polls every 5 seconds.
2. New rows of that type go to the old worker. Rows already routed to the service continue there.
3. Rows already on the service are not moved back. Moving them would need a non-transactional handoff across the broker, which could re-send. If the service must stop for a long time, its queue is the backlog. The fix is to restore the service, not to move rows.
4. Verify with the reconciliation query in step 6.

## Open items to confirm before step 1

- MailRelay's behavior when a keyed send returns an error after acceptance. The plan assumes a retry with the same key is dropped.
- Whether the 24-hour key window is per account or per send type. The plan assumes per account.
- Whether PII (email and payload) in the broker is acceptable under the broker's retention and access policy.
- The exact retention for the service's `jobs` table. The plan assumes 30 days, which must exceed any relay republish delay.
- Owners for the sweeper, reconciliation, and latency alerts.
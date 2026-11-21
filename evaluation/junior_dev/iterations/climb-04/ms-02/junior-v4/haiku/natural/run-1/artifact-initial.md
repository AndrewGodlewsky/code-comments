# Plan: Extract notifications into a Notification Service

## Invariants the plan keeps

1. **Callers unchanged.** `enqueue_notification(tx, ...)` still inserts into the monolith `notifications` table inside the caller's transaction. That row is the first record.
2. **One owner per row.** Each row's route (`monolith` or `service`) is set once, at insert, from a per-type flag. No row ever changes owner. Only one system ever sends a given notification, so a flag flip cannot make both sides send or drop a row.
3. **Separate data.** The service has its own database. The monolith reads and writes only its own database. The only shared channel is the broker, which is at-least-once.
4. **Idempotent sends.** Every MailRelay send passes `idempotency_key = notification id`, on the old worker and the service.
5. **Send window.** Every send attempt for a notification must happen within 23 hours of its `created_at`. MailRelay dedupes keys for 24 hours, so every send for one key falls inside one dedupe window. A send that would fall outside the window is marked failed and paged instead. Today's retry policy never reaches this limit (total backoff is 15 minutes), so this only affects outages and redeliveries. It is an addition to the brief, flagged for sign-off below.
6. **Inbox dedupe.** The service's notification id is its primary key. An insert that conflicts is ignored, never reset to pending.

## Data and state

**Monolith `notifications` (additions only)**

- `route` text, NOT NULL, default `'monolith'`. Set at insert from `flags.get("notifications.route." + type)`. Any value other than `'service'`, or a flag read that fails, yields `'monolith'`.
- `render_hash` text, nullable. Written by the old worker at send time. Used for shadow parity.
- `publish_claimed_until` timestamp and `published_at` timestamp. Used by the outbox publisher.
- `completed_at` timestamp. Set by the completion consumer.
- Partial indexes on `(route, status, next_attempt_at)` and `(route, published_at)`.

**Service database**

- `notifications`: `id` (PK, same UUID as the monolith row), `type`, `email`, `payload`, `status` (`shadow`, `pending`, `sent`, `failed`), `attempts`, `next_attempt_at`, `lease_until`, `created_at` (copied from the monolith), `received_at`, `sent_at`.
- `outbox`: completion and shadow-report events, written in the same transaction as the status change.
- Retention: keep rows for at least max(broker retention, 48 hours). The inbox dedupe must outlive any redelivery or republish.

**Message (`notifications` topic)**: `{schema_version, id, type, email, payload, created_at, mode: "live" | "shadow"}`.

**Completion event**: `{id, outcome: "sent" | "failed", sent_at}`. Shadow reports carry `{id, render_hash}` on the same channel.

**Service send algorithm (per row, committed per row, no DB transaction held across the MailRelay call)**

1. Claim due rows with `FOR UPDATE SKIP LOCKED`, set `lease_until = now() + 2 min`, and increment `attempts` in the claim commit.
2. If `attempts > 5`, or `now() > created_at + 23h`, mark failed, page on-call, and emit the outcome. Do not send. (If `attempts > 5` because a crash consumed the last attempt, the outcome is unknown. On-call checks MailRelay by key.)
3. Render with the shared template package. Send with `idempotency_key = id`.
4. On success, mark `sent`, clear the lease, and write the completion event to the outbox.
5. On error (including timeouts), if `attempts >= 5`, mark failed, page on-call, and write the completion event. Otherwise set `next_attempt_at = now() + BACKOFF[attempts - 1]` and clear the lease. Backoff is 1, 2, 4, 8 minutes.

Attempt counting moves to the claim. A crash mid-send therefore consumes an attempt, which bounds crash loops. Otherwise the policy is unchanged.

**Monolith `created_at` note.** `now()` in a Postgres-style insert is the transaction start time, not the commit time. It is slightly early, which is conservative for both the latency gate and the 23-hour cutoff.

## Steps, in shipping order

### Step 1. Idempotency key and send window on the old worker

- **Starts:** deploy of the monolith with the change. No type has moved.
- **Data moves:** none. The old worker adds `idempotency_key=row.id` to `mailrelay.send`. It also applies the 23-hour cutoff (mark failed and page instead of sending).
- **State:** unchanged monolith `notifications` table.
- **If something fails:**
  - A crash after MailRelay accepts a batch item but before the batch commit leaves the row pending. The retry carries the same key, MailRelay drops it and returns success, and the row is marked sent. This is the fix for the roughly 30 duplicates a week.
  - MailRelay down or timing out: unchanged retry behaviour. A timed-out send may have been accepted, and the key makes the retry safe.
  - A duplicate that persists after this step is outside the 24-hour window and needs investigation.
- **Gate:** in staging, confirm that a second send with the same key returns success without a second delivery. Confirm this with MailRelay before production. Duplicate tickets trend down.

### Step 2. Route column and routing seam in the monolith

- **Starts:** migration, then deploy. Routing flags exist, all set to `monolith`. Nothing routes to the service yet.
- **Data moves:** none. Existing rows get `route = 'monolith'` through the column default. New rows get `route` from the flag at insert.
- **Changes:**
  - The old worker's selection gets `AND route = 'monolith'`. This is required before any type moves. Without it the old worker would send service-routed rows as well.
  - `enqueue_notification` keeps its signature and reads the flag inside a try/catch that defaults to `monolith`.
  - Add `render_hash` (the old worker writes it at send time) and the outbox columns.
- **State:** monolith DB only.
- **If something fails:**
  - Flag service unreachable: falls back to `monolith`. The caller's transaction still commits.
  - Migration on a large table: use a metadata-only default and build indexes concurrently.
  - Crash, broker and MailRelay behaviour: identical to step 1.

### Step 3. Outbox publisher in the monolith (no traffic yet)

- **Starts:** a background loop on every monolith instance, the same shape as the old worker. It claims rows with `route = 'service' AND published_at IS NULL AND (publish_claimed_until IS NULL OR publish_claimed_until < now())`, using `SKIP LOCKED`.
- **Data moves:** monolith row → broker message. The publisher publishes only after the row is committed, so uncommitted rows are never published.
- **State:** the claim lease is set in a short transaction, which is committed before the broker call. No transaction is held across the broker call. `published_at` is set after broker confirmation. The broker holds the message.
- **If something fails:**
  - Broker down: rows stay unpublished and retry with backoff. Enqueue is unaffected because it only inserts a row. Alert on publish lag.
  - Crash after claim: the lease expires and the row is republished.
  - Crash after broker confirmation but before `published_at`: a duplicate message. The service inbox absorbs it (step 4).
- **Gate:** zero messages published while no row has `route = 'service'`. Publish lag and error metrics are wired to alerts.

### Step 4. Notification Service in shadow mode

- **Starts:** deploy of the service with its own database and its own consumer group on the `notifications` topic. The publisher also sends shadow copies of a sample of monolith-routed rows, with `mode = "shadow"`.
- **Data moves:** broker message → service `notifications` row. Shadow rows get status `shadow`.
- **Consumer:** in one transaction, `INSERT ... ON CONFLICT (id) DO NOTHING`, then commit, then ack. It never calls MailRelay and never waits on a send, so it stays well inside the 30-second ack window.
- **Shadow:** the service renders each shadow copy with the shared template package and emits a shadow report with its render hash. A monolith consumer compares it with the `render_hash` on the row. Mismatches are alerted.
- **Shared templates:** the template package is pinned to one version in both systems. Template changes for any type are frozen during the rollout, so rollback renders the same text.
- **State:** the service DB. The service never reads the monolith DB.
- **If something fails:**
  - Consumer crash after insert but before ack: redelivery, insert conflicts, ack. No duplicate.
  - Service DB down: no ack, so the broker redelivers after 30 seconds, possibly to another consumer. The inbox absorbs it.
  - Redelivery of a row already `sent` (for example, after step 6): the conflict leaves the status alone, so no resend.
  - MailRelay: not involved in shadow mode.
- **Gate:** shadow render parity is 100 percent for all three types over several days. The service absorbs a load test of 2x combined peak (shipping, order and reset) with stable consumer lag. The 23-hour cutoff and dedupe-retention settings are confirmed.

### Step 5. Completion return path and reconciler

- **Starts:** deploy of the service outbox publisher, the monolith completion consumer, and the monolith reconciler (every 5 minutes).
- **Data moves:** service terminal state → completion event → monolith row status. The completion consumer runs `UPDATE ... SET status = ..., completed_at = ... WHERE id = ? AND route = 'service' AND status = 'pending'`. This is idempotent.
- **Reconciler (monolith DB only):** for `route = 'service'`, `status = 'pending'`, and `published_at` older than 30 minutes:
  - If `created_at` is older than 23 hours, mark failed and page. The service would refuse the send anyway.
  - Otherwise republish the message. The service's inbox dedupes it. If the row is already terminal, the service re-emits the completion event.
- **State:** the monolith DB holds the terminal status. The service outbox holds events until they are published.
- **If something fails:**
  - Lost completion event: the reconciler's republish causes the service to re-emit it.
  - Broker retention expires before the service consumes: the reconciler republishes a row that is still within 23 hours. A row older than that is failed and paged, not republished, so no send can happen past the window.
  - Duplicate events are harmless, because the monolith update is conditional on `status = 'pending'`.
- **Gate:** every committed `route = 'service'` row is terminal, or inside its SLA, in the reconciler's output. The reconciliation count is the audit that every committed notification ends accepted or failed-and-paged.

### Step 6. Cut over `shipping_update` (at least 3 days)

- **Starts:** set `notifications.route.shipping_update = service`. The flag reaches every instance within 10 seconds.
- **Data moves:** new shipping rows are stamped `service`. Existing rows are not moved. Monolith-routed rows already in flight drain through the old worker.
- **State:** the `route` column on each row. Nothing else changes.
- **If something fails:**
  - Service down: messages queue in the broker and service DB. Consumer lag alerts fire. If the lag is sustained, roll back.
  - Broker down: the monolith outbox backs up. No rows are lost, and they are sent when the broker recovers. Publish-lag alert fires.
  - MailRelay down: the service retries on the same schedule. After 5 attempts the row is marked failed and paged.
  - Redelivery: covered by the inbox.
- **Rollback (flag flip, under 1 minute):** set the flag back to `monolith`. New rows go to the old worker. Service-routed rows keep their owner and finish on the service, so nothing is lost and nothing is re-sent. Keep the service running until its pending rows and the monolith publisher backlog for that type reach zero.
- **Gate:** 3 days. Zero duplicate sends, checked against the send log keyed by notification id. Every committed row is accounted for by reconciliation. Latency is recorded.

### Step 7. Cut over `order_confirmed` (at least 3 days)

- **Starts:** at least 3 days after step 6. Same flag flip, same behaviour, same rollback.
- **Gate:** 3 days. The p99 latency gate is measured on this type's window (see the definition below). The service's measured p99 must be under 60 seconds before step 8 starts.

### Step 8. Cut over `password_reset`, after the p99 gate

- **Starts:** the `order_confirmed` window is at least 3 days, and its p99 enqueue-to-MailRelay is under 60 seconds. Earliest start is day 6 counting from step 6.
- **Data moves and state:** as in steps 6 and 7.
- **Latency budget:** the outbox poll, the broker, the consumer insert, the service poll interval, and MailRelay together must fit under 60 seconds at p99 on normal days. A MailRelay degradation adds retry backoff, so the gate needs a decision (see open questions).
- **If something fails:** as in step 6. Password reset is latency-sensitive, so alert on p99 separately during the window, not only on daily totals.
- **Gate:** run on the service for at least 7 days. The old worker stays deployable for this whole period.

### Step 9. Decommission the old worker (earliest day 13)

- **Starts:** `password_reset` has run on the service for 7 days. All gates from steps 6 to 8 are clean. The drain conditions hold: no monolith-routed pending rows for any type, no service-routed pending rows, and a zero monolith publisher backlog.
- **Actions:** remove the old worker's `run_worker` from deploy and remove the monolith's sending path and templates. Keep the `route` column, the publisher, the completion consumer, and the reconciler. The monolith `notifications` table stays as the first record and needs its own retention policy.
- **Consequence:** rollback to the monolith is no longer possible after this step. The plan makes this a deliberate, separate decision.

## Timeline (earliest)

| Day | Event |
|---|---|
| 0 | `shipping_update` moves to the service |
| 3 | `order_confirmed` moves |
| 6 | `password_reset` moves, after the p99 gate |
| 13 | Old worker removed (7 days after `password_reset`) |

Steps 1 to 5 happen before day 0 and are not on the critical path. Shadow mode must be clean before day 0.

## Open questions and decisions for sign-off

1. **MailRelay key semantics.** Confirm that the key dedupes within 24 hours, that a timed-out send counts as accepted when a key is reused, and whether the window is counted from first acceptance. Everything else depends on this.
2. **23-hour send window.** This is an addition to the brief. Approve it, or give an alternative bound that keeps all sends inside MailRelay's dedupe window.
3. **p99 definition.** Should the 60-second gate include retry time? Measured with retries, a MailRelay degradation can breach the gate even when the service path is healthy. Proposed: report p99 both with and without retries, and gate on the first-attempt p99 unless the business wants retries included.
4. **Broker retention versus dedupe horizon.** Service rows must outlive broker retention and the 23-hour window. Confirm the broker's retention period.
5. **PII on the broker.** Messages carry email addresses and payloads. Confirm topic encryption and access control are acceptable.
6. **Template freeze.** Confirm that the shared template package can be frozen per type during each rollout window.
7. **Rollback after step 9.** The plan treats decommission as the end of rollback. Confirm that this is acceptable.
8. **Per-row commit on the old worker.** Not required, because the key removes the duplicate risk. Optional for lowering batch lock time.
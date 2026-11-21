# Plan: Extract notifications into a Notification Service

## Core design rule

Every notification has exactly one **owner**, either `monolith` or `service`. The owner is written once, in the caller's own transaction, by `enqueue_notification`, and it is never changed afterwards. Flags only decide the owner of rows enqueued after a flip. Because no row is ever re-owned, two senders never race for the same notification, and rollback never has to move in-flight work.

Two more rules follow from the brief:

- **Idempotency key.** Every MailRelay send carries `idempotency_key = notifications.id`. MailRelay drops a repeat of a key it accepted in the last 24 hours and returns success. This protects retries and crash recovery only within that 24-hour window. The service's own inbox table is what protects against broker redelivery beyond it (see Step 4).
- **Retry policy is unchanged.** 5 attempts, backoff of 1, 2, 4 and 8 minutes, then `failed` and page on-call. Crash recovery counts as an attempt, so crashes do not extend the budget.

Data flow once the cutover is complete:

```
checkout tx --INSERT (owner=service)--> monolith notifications (outbox)
monolith relay --publish requested--> broker --consume, INSERT, ack--> service DB
service sender --send(key=id)--> MailRelay
service --status events--> broker --> monolith notifications (mirror, forward-only)
```

---

## Steps, in ship order

Each step lists what starts it, what data moves, where state lives, and what happens on failure.

### Step 1. Confirm platform facts (no code)

- **Starts:** plan approval.
- **Data moves:** none.
- **State:** none.
- **Confirm:**
  - MailRelay honours `idempotency_key` on the real API, including its 24-hour window and the success response on a duplicate.
  - The broker's retention period and the longest redelivery horizon it allows.
  - Whether the broker supports message-id dedupe. Do not rely on it.
  - Clock skew between hosts (needed for the latency gate in Step 8).
- **On failure:** if MailRelay does not honour keys, stop. Steps 1 and 4 depend on it. If broker retention is unknown, Step 4 cannot size the inbox retention.

### Step 2. Pass the idempotency key on the old worker

- **Starts:** deploying the change to `_deliver` in `app/notifications.py`, which calls `mailrelay.send(..., idempotency_key=str(row.id))`. This applies to every type, before any type moves.
- **Data moves:** none new. The key is the existing row id.
- **State:** unchanged monolith `notifications` table.
- **Effect:** a crash after MailRelay accepts a send but before the batch commit re-sends the same key. MailRelay drops it. This should remove the roughly 30 weekly duplicates, because the retry happens within minutes, well inside the 24-hour window.
- **On failure:**
  - MailRelay down or timing out: the existing retry path handles it. A timeout is ambiguous, but the key makes the retry safe.
  - Key rejected by the API: treat as a `mailrelay.Error`, which retries and eventually pages. Roll back the deploy if it persists.
  - Redelivery: not applicable. This is the polling path.
- **Verify:** duplicate-email support count falls. Count MailRelay duplicate-drop responses to confirm the key is taking effect.

### Step 3. Add ownership to the monolith outbox and make the worker respect it

- **Starts:** a migration, then a deploy.
- **Schema change** (additive, so old code can ignore it):
  - `owner text not null default 'monolith' check (owner in ('monolith','service'))`
  - `service_published_at timestamptz null`
  - `service_state text null` (`received`, `accepted`, `failed`)
  - `service_state_at timestamptz null`
  - `shadow_published_at timestamptz null` (used in Step 6)
  - `rendered_sha256 text null` (used in Step 6)
  - A partial index on `created_at` where `owner = 'service' and service_published_at is null`.
- **Code:**
  - The worker query gains `AND owner = 'monolith'`.
  - `enqueue_notification` reads `flags.get('notifications.owner.<type>')`, defaulting to `monolith`, and writes `owner` in the same `INSERT`. Callers are unchanged.
- **Data moves:** none.
- **State:** monolith DB only.
- **Ordering gate:** every monolith instance must run the owner-aware worker before any flag is set to `service`. An older instance without the filter would send service-owned rows.
- **On failure:**
  - Flag unreadable: default to `monolith`, which is always safe.
  - Crash: the `INSERT` and the flag decision are in the caller's transaction, so there is no partial state.
  - Rollback: revert the code. The new columns can stay.

### Step 4. Build the Notification Service, dark

- **Starts:** deploying the service with its own database. Its consumer subscribes to the `notification.requested.v1` topic.
- **Message:** `{id, type, user_id, email, payload, created_at, schema_version}`, keyed by `id`.
- **Service database:**
  - `inbox_notifications`: `id` (primary key), `type`, `user_id`, `email`, `payload` (jsonb), `mode` (`live` or `shadow`), `state` (`queued`, `sending`, `accepted`, `failed`, `shadow`), `attempts`, `first_attempt_at`, `next_attempt_at`, `lease_expires_at`, `last_error`, `created_at` (the monolith's timestamp), `received_at`.
  - `status_outbox`: rows of events to publish.
- **Consumer:** `INSERT ... ON CONFLICT (id) DO NOTHING`, commit, then ack. Acking only after the commit, and never waiting on MailRelay, keeps every ack well inside the 30-second redelivery window.
- **Sender:**
  - Claims due rows with a lease (`lease_expires_at`, around 60 s, longer than the MailRelay timeout of about 20 s) and `FOR UPDATE SKIP LOCKED`.
  - Renders the template (a copy of `templates.render`).
  - Sends with `idempotency_key = id`.
  - On success, sets `accepted`.
  - On failure, applies the retry policy. At 5 attempts it sets `failed` and pages on-call.
  - Sending is disabled by config (`send_enabled = false`) until Step 7.
- **Resend guard (new, needs sign-off):** a lease-expired row is re-sent only if `first_attempt_at` is less than 23 hours ago. Otherwise it is marked `failed` and paged. This stops a long outage from taking a row past the MailRelay 24-hour dedupe window.
- **Data moves:** the message payload into the service DB. Nothing goes back to the monolith yet.
- **State:** the service database only.
- **On failure:**
  - Crash before the commit: no ack, so the broker redelivers and the insert succeeds.
  - Crash after the commit but before the ack: the redelivery hits `ON CONFLICT` and is acked. No duplicate row.
  - Service database down: the consumer does not ack, so messages wait in the broker. Monitor queue depth and oldest message age. Retention limits must cover the outage.
  - Crash during send: the lease expires, the row is re-claimed, and it is re-sent with the same key within the 24-hour window. MailRelay drops the duplicate. The reclaim counts as an attempt.
  - MailRelay down: the normal retry schedule applies, then `failed` and page.
  - Redelivery after the row is final: `ON CONFLICT` makes it a no-op.
- **Retention:** keep inbox rows for at least the longer of 30 days or the broker's redelivery horizon. This is the dedupe horizon.
- **Gate:** staging tests with synthetic messages covering crash-at-each-point, redelivery, and MailRelay faults.

### Step 5. Status back-channel and monolith reconciliation

- **Starts:**
  - The service writes `received`, `accepted`, and `failed` events to `status_outbox` in the same transaction as the state change. A relay publishes them after commit.
  - The monolith consumes `notification.status.v1`.
  - A monolith reconciler runs on a timer.
- **Monolith status consumer:** updates `service_state` and `service_state_at` on the row, and mirrors `status` to `sent` or `failed` so existing support tooling keeps working. Updates only move forward in rank (`received` < `accepted` or `failed`), so replays are harmless.
- **Reconciler:** re-publishes rows where `service_published_at` is set, `service_state` is null, the row is older than 10 minutes, and it is younger than 7 days. The 7-day limit stays inside the service's dedupe retention.
- **Data moves:** notification ids and states from the service back to the monolith. No email or payload travels this way.
- **State:** service `status_outbox`; monolith `notifications` row.
- **On failure:**
  - Broker down: status events queue in the service outbox and are published later.
  - Lost broker message: the reconciler re-publishes and the service dedupes.
  - Service down: the reconciler republishes stale rows. Page on any row stuck in `service_published_at` without `service_state` beyond a threshold, for example 10 minutes.
  - Duplicate status event: forward-only updates make it harmless.

### Step 6. Shadow-run the first type (`shipping_update`)

- **Starts:** setting `notifications.shadow.shipping_update` on. The monolith relay publishes a copy of each `shipping_update` row with `mode = shadow`, setting `shadow_published_at`.
- **Monolith:** the old worker still sends the row and now writes `rendered_sha256` alongside the send.
- **Service:** renders the shadow copy and records the hash. It never calls MailRelay for `mode = shadow` rows, and the sender filters on `mode = live`.
- **Comparison:** the service reports its hash in the status event, and a dashboard compares it with `rendered_sha256`.
- **Gate:** zero unexplained mismatches over at least 24 hours. Freeze template edits for the type while shadowing.
- **Data moves:** a copy of each row, including email, to the service DB, which is the same data that will move at cutover.
- **State:** shadow rows live in the service inbox with state `shadow`.
- **On failure:**
  - Service down: shadow copies queue. The monolith keeps sending, so no user impact.
  - Crash or redelivery: the `ON CONFLICT` insert stays idempotent, and shadow rows can never reach MailRelay.

### Step 7. Cut over `shipping_update`

- **Starts:** setting `notifications.owner.shipping_update = service`, after the Step 6 gate. Set `send_enabled = true` on the service before this flip.
- **Effect:** new `shipping_update` rows get `owner = service` within about 10 seconds. The relay publishes them, and the service sends them. Rows already `monolith`-owned are sent by the old worker, to completion.
- **Data moves:** new rows only. Each goes through the outbox, the broker, and the service in turn.
- **State:** the flag store, the monolith outbox, and the service inbox.
- **Monitor:** enqueue-to-accepted p99, backlog age, `failed` count, and pages. Hold for at least 3 days before Step 8.
- **Rollback (flag flip):** set the flag back to `monolith`. New rows are owned by the monolith within 10 seconds, and the old worker picks them up within its 5-second poll. Rows already owned by the service keep going on the service. Pending outbox rows are still published and sent by the service. Nothing is re-owned, so nothing is lost or re-sent.
- **Emergency only:** a service outage delays already-owned rows, and a flip does not speed them up. If the service must be bypassed, an operator can re-own rows with `service_state` null and an age under 24 hours. Re-sending with the same key is safe inside that window. This needs explicit approval.
- **On failure:**
  - Service down during the cutover: owned rows queue in the broker and the service DB. Latency rises, nothing is lost. Flip new rows back if the outage is long.
  - Broker down: the relay retries, and rows stay pending.
  - MailRelay down: retries, then `failed` and page.

### Step 8. Cut over `order_confirmed`, and measure the latency gate

- **Starts:** setting `notifications.owner.order_confirmed = service` after `shipping_update` has run on the service for at least 3 days.
- **Mechanics:** the same as Step 7, including the rollback behaviour.
- **Latency gate (for Step 9):** over at least 3 days on the service, the p99 of `service accepted_at minus monolith created_at` for `order_confirmed` rows is under 60 seconds.
- **Interpretation to decide:** the metric as written includes retries. The first retry waits 1 minute, so any retried row exceeds 60 seconds. If MailRelay failures exceed about 1%, the p99 will fail even when the pipeline is healthy. Recommended: gate on the strict metric, which includes retries, and report the first-attempt p99 alongside it.
- **Clock skew:** if skew exceeds about 1 second, measure the two halves separately.
- **Latency budget:** the relay poll interval, the broker, the consumer, and the sender all count. Set the relay poll to about 1 second.
- **Data moves and state:** as in Step 7.
- **On failure:** if the gate fails, stay on the monolith for `order_confirmed` and fix the latency. Do not start Step 9.

### Step 9. Cut over `password_reset`

- **Starts:** setting `notifications.owner.password_reset = service` after the Step 8 latency gate has passed.
- **Mechanics:** the same as Step 7. This is user-blocking, so watch the p99 closely.
- **Hold:** keep the old worker deployable for 7 days after this flip.
- **Rollback:** the flag flip, as in Step 7.
- **On failure:** as in Step 7.

### Step 10. Decommission the old worker

- **Starts:** 7 days after `password_reset` has run on the service.
- **Preconditions:**
  - Zero `owner = monolith` rows pending.
  - No shadow rows remaining.
  - The reconciler reports no stuck rows.
  - All three owners are `service`.
- **Action:** remove the sender path in `run_worker` and `_deliver`, and remove the template import from the monolith if nothing else uses it. Keep the outbox relay, the status consumer, and the reconciler.
- **After this point:** rollback is a redeploy, not a flag flip. Say so in the change ticket.
- **Outbox retention:** purge monolith outbox rows once they are final and older than 30 days. The service's dedupe horizon is independent.
- **On failure:** if any precondition fails, do not remove the worker. Investigate first.

---

## Cross-cutting failure modes

- **Service-side outage paging:** the service only pages on its own failures. Backlog age and stuck-status alerts (Steps 4 and 5) must catch a fully dead service.
- **Template drift:** the service's template copy must match the monolith's during shadow and cutover. Freeze template edits for a type from Step 6 until its decommission, or version templates.
- **Personal data:** the service stores email addresses. User deletion and retention need an owner and a propagation path, from the monolith to the service.
- **Duplicate-send guarantee:** every send path uses the notification id as the key, and the service dedupes by id. The residual risk is a send after the 24-hour MailRelay window, which the 23-hour resend guard in Step 4 narrows.

## Open questions and assumptions

1. Broker retention and maximum redelivery horizon (sets the service's inbox retention).
2. Whether the 23-hour resend guard is acceptable as a new policy, since the brief says to keep retries exact.
3. Whether the Step 8 latency gate includes retries.
4. Clock skew between monolith and service hosts.
5. Retention of email addresses in the service, and how erasure propagates.
6. Whether MailRelay's key window starts at first acceptance (assumed, not stated in the overview).

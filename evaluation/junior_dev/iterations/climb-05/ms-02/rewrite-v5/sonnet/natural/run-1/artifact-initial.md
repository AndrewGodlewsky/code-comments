# Plan: extract notifications into a Notification Service

## Design in brief

- **Arbiter.** The monolith `notifications.status` column decides who owns a notification. It moves `pending` -> `handed_off` -> `sent` or `failed`. The routing flag only decides what happens to rows that are still `pending`. This makes rollback safe.
- **Hand-off.** A new **dispatcher** in the monolith publishes `pending` rows of service-routed types to the broker. It marks them `handed_off` only after the broker confirms storage. `enqueue_notification` and its callers do not change.
- **Sending.** The service stores each request in its own database, using the notification id as a unique key. It renders the template, sends to MailRelay with `idempotency_key = id`, and commits once per notification, not once per batch.
- **Results.** The service publishes a `sent` or `failed` result event. A monolith consumer applies it to the monolith row, so the first-recorded row ends up with the true outcome.
- **Why duplicates cannot reach a user.**
  - Every crash window (after MailRelay accepts but before a commit, broker redelivery, a dispatcher crash after publish, a stale flag) ends in a repeated send with the same key.
  - MailRelay drops a repeated key for 24 h. The longest retry chain is 1+2+4+8 = 15 min.
  - Every repeated broker message is also deduplicated by id in the service database.
- **Retries.** The policy is unchanged: 5 attempts, waits of 1/2/4/8 min, then `failed` and a page. The `attempts` count and `next_attempt_at` travel with the hand-off message, so a notification that already used attempts on the old worker keeps its count.

### Where state lives

| State | Owner |
|---|---|
| Notification recorded (first record) | Monolith `notifications` row, written in the caller's transaction |
| Handed off or not | Monolith `status` (`handed_off`) |
| Attempts, backoff, lease, sent or failed (service-owned rows) | Service database |
| Final outcome mirrored back | Monolith row, via result event |
| Routing per type | Monolith flag `notif.route.<type>` = `monolith` or `service`, default `monolith` |

### Messages (broker topics)

- `notification.requested`
  - Fields: `id, type, user_id, email, payload, attempts, next_attempt_at, created_at`
  - Direction: monolith -> service
- `notification.result`
  - Fields: `id, status (sent|failed), attempts, finished_at`
  - Direction: service -> monolith

## Steps, in shipping order

### Step 1. Pass `idempotency_key` on the old worker

- **Trigger:** first change shipped. It is a code change to `_deliver`: `mailrelay.send(..., idempotency_key=row.id)`.
- **Data moved:** none. The notification id is sent to MailRelay as the key.
- **State:** unchanged (monolith `notifications`).
- **Failures:**
  - Crash after MailRelay accepts but before the batch commit: the rows stay `pending` and are re-sent, but MailRelay drops the duplicate within 24 h and returns success. The worker then marks the row `sent`. This fixes the roughly 30 duplicates a week.
  - Timeout where MailRelay actually accepted: the retry carries the same key and is dropped.
- **Exit check:** the weekly duplicate-email count in support falls to about zero. Nothing moves until this is deployed on every instance.

### Step 2. Monolith groundwork, with no behavior change

- **Trigger:** deploy after step 1. Work:
  - Migration: allow the status `handed_off`, and add `handed_off_at`. Add an index on `(status, type, created_at)`.
  - Flags `notif.route.shipping_update`, `notif.route.order_confirmed` and `notif.route.password_reset`, all `monolith`.
  - Change the worker query to add `AND type = ANY(<types whose flag is 'monolith'>)`, read from `flags.get` on each loop.
- **Data moved:** none.
- **State:** monolith table and flags.
- **Failures:**
  - Mixed fleet during rollout: an old-version worker without the filter may pick up a row. It sends with the idempotency key and is still correct, because flags are all `monolith` at this point.
  - A stale flag (up to 10 s) only means a row is picked by the other path. The row lock or status arbitrates, as described under Step 5.
- **Exit check:** all instances are on the new version before any flag is flipped.

### Step 3. Build and deploy the Notification Service (dark, no traffic)

- **Trigger:** deploy and subscribe to `notification.requested`, with no producer yet.
- **Service database:**
  - `notifications(id PK, type, email, payload, attempts, next_attempt_at, created_at, status pending|sent|failed, lease_until, result_published_at, paged_at)`
- **Consumer flow:**
  1. On message, insert the row `ON CONFLICT (id) DO NOTHING` and commit.
  2. Ack only after the commit.
  3. Nudge the sender so a new row is sent immediately, with no polling delay.
- **Sender loop:**
  1. Claim one due row: `status='pending' AND next_attempt_at <= now() AND lease_until < now()`, using `SKIP LOCKED`. Set `lease_until = now()+60s`.
  2. Render the template (rendering now lives here). Call `mailrelay.send(..., idempotency_key=id)`.
  3. Commit that one row's result immediately:
     - Success: `sent`.
     - Error or timeout, attempt < 5: `attempts+1` and `next_attempt_at = now() + [1,2,4,8] min`.
     - Error or timeout, attempt 5: `failed`.
- **Result publisher:** scans terminal rows with `result_published_at IS NULL`, publishes `notification.result`, waits for the broker confirmation, then sets `result_published_at`.
- **Pager:** pages on-call for `failed` rows with `paged_at IS NULL`, then sets `paged_at`.
- **Duplicate request for a row already `sent` or `failed`:** the service re-emits the result event and does not send again.
- **Failures:**
  - Crash after MailRelay accepts but before commit: the lease expires, another instance re-sends with the same key, and MailRelay drops it.
  - Redelivered broker message (no ack within 30 s): the insert is a no-op.
  - MailRelay down: the retry schedule applies, so after about 15 min of outage the rows fail and are paged, exactly as today.
  - Broker down: the consumer idles. Results queue in the service database (`result_published_at` is null) and publish on recovery. Sending still proceeds for rows already stored.
  - A slow send that outlives its lease allows a second instance to send. The key makes it harmless.
- **Verification (staging, fake MailRelay with key de-duplication):**
  - Render parity: golden payloads for all three types must be byte-equal with the monolith templates.
  - Kill the service mid-send.
  - Redeliver messages.
  - Run a MailRelay outage and confirm the retry timing and the page.

### Step 4. Add the dispatcher and result consumer to the monolith (idle)

- **Trigger:** deploy after step 3 is healthy. Both components are inert while all flags are `monolith`.
- **Dispatcher** (loop every 1 s, one DB connection per instance):
  1. In one transaction, `SELECT ... WHERE status='pending' AND type = ANY(<types routed to service>) ORDER BY created_at LIMIT 100 FOR UPDATE SKIP LOCKED`.
  2. Publish each row as `notification.requested`, including its current `attempts` and `next_attempt_at`.
  3. Wait for the broker confirmations.
  4. `UPDATE ... SET status='handed_off', handed_off_at=now()`, then commit.
- **Result consumer:**
  - On `notification.result`, run `UPDATE notifications SET status=<result>, attempts=<n> WHERE id=<id> AND status <> 'sent'`, then commit, then ack. It is idempotent.
  - A `sent` result may override `failed`. In that rare split case on-call was already paged, and the runbook says to reconcile by hand.
- **Reconciler** (every 15 min): for rows still `handed_off` for over 1 h, republish `notification.requested`. The service ignores it if the row is in progress and re-emits the result if it is terminal. Alert if any row is still `handed_off` after 2 h.
- **Failures:**
  - Crash before the broker confirms: the lock is released, the row stays `pending`, and the next run republishes it. Either dispatcher can pick it up.
  - Crash after the confirm but before the commit: the row is republished and the service deduplicates by id.
  - Broker down: rows stay `pending` and nothing is lost. An alert fires when the oldest `pending` row of a service-routed type is older than 30 s. The runbook is to flip the type back (see Rollback below). Because those rows are still `pending`, the old worker sends them with the key and nothing is duplicated.
  - Dispatcher and old worker on the same row: both use `FOR UPDATE SKIP LOCKED`, so exactly one claims it. Even if a crash lets both send, the shared key stops the second email.

### Step 5. Cut over `shipping_update` (day 0)

- **Trigger:** set `notif.route.shipping_update = service`. It takes effect on every instance within 10 s.
- **Data moved:**
  - New `shipping_update` rows (about 40,000 a day) are handed off to the service.
  - `pending` rows that are mid-retry are handed off with their `attempts` and `next_attempt_at`, so they keep the same 5-attempt budget.
  - The old worker no longer selects this type.
- **State:** the service database owns `handed_off` rows. The monolith row mirrors the outcome through result events.
- **Failures:** see Steps 3 and 4. The monolith row is the safety net, because it is `pending` until the broker confirms.
- **Day-0 rollback drill:**
  1. After about 1 hour on the service, flip back to `monolith`, then confirm that new rows go through the old worker.
  2. Confirm that rows already handed off still finish on the service and that no email is sent twice.
  3. Flip forward again.
- **Soak:** at least 3 full days. Watch send success rate, `handed_off` backlog, duplicate-email count (expect 0), pages, and the age of the oldest `pending` row.

### Step 6. Cut over `order_confirmed` (earliest day 3)

- **Trigger:** `shipping_update` has run on the service for at least 3 days with no unresolved incidents. Then set `notif.route.order_confirmed = service`.
- **Data moved:** about 12,000 rows a day, handled the same way as step 5.
- **Latency gate:** the service must record enqueue-to-MailRelay latency per notification, taken from `created_at` in the message to the time MailRelay accepts. Keep it as a p99 over rolling windows. Give the service and monolith synchronized clocks. The dispatcher's 1 s poll, a broker hop and the immediate-send nudge give plenty of headroom against the 60 s target.
- **Failures:** same as step 5. Rolling this type back restarts its 3-day clock and the next type's start.
- **Soak:** at least 3 days, with the p99 measured throughout.

### Step 7. Cut over `password_reset` (earliest day 6)

- **Trigger, both required:**
  1. `order_confirmed` has run on the service for at least 3 days.
  2. The service's p99 enqueue-to-MailRelay latency on `order_confirmed` was under 60 s over that period. If it was not, stay put and fix the cause first.
- **Action:** set `notif.route.password_reset = service` (about 1,500 rows a day).
- **Extra alerts for this type:** the oldest `pending` password_reset row older than 30 s, and the p99 over 60 s. Either should lead to an immediate flip back, which is safe as described in Step 4.
- **Failures:** same as steps 5 and 6. Rolling back restarts this type's 7-day decommission clock.

### Step 8. Decommission the old worker (earliest day 13)

- **Trigger:** `password_reset` has run on the service for at least 7 days. Also confirm that no non-terminal `pending` rows remain for any type, apart from the normal in-flight tail.
- **Action:**
  - Remove `run_worker`, `_deliver`, the `monolith` branch of the filter and the monolith template rendering code.
  - Keep `enqueue_notification`, the dispatcher, the result consumer and the reconciler. Keep the hand-off flags until you remove them in a later cleanup, but they are no longer a rollback route.
- **After this step**, rollback to the monolith is no longer possible. This is the reason for waiting a full 7 days before the step.
- **Failures:** if removing the worker causes trouble, redeploy the previous build, which still contains it.

## Rollback (any type, any time after step 5)

1. Set `notif.route.<type> = monolith`. It takes effect on every instance within 10 s.
2. New rows stay `pending`, and the old worker picks them up with the idempotency key.
3. Rows already `handed_off` are not touched. The service keeps retrying them, publishes their results, and the monolith consumer records them. Nothing is re-sent, because the monolith never re-sends a `handed_off` row.
4. Keep the service and the broker consumers running until the type's `handed_off` backlog reaches zero (at most about 15 min plus the broker window).
5. A stale flag on a single instance for up to 10 s can still hand off a row. The row is then owned by the service. Because ownership is decided by the `status` column and not by the flag, it is still sent once.

## Timeline

| Day | Event |
|---|---|
| 0 | Step 1 deployed first; steps 2 to 4 follow, then `shipping_update` moves (step 5) |
| 3 earliest | `order_confirmed` moves (step 6) |
| 6 earliest | `password_reset` moves (step 7), if p99 < 60 s on `order_confirmed` |
| 13 earliest | Old worker removed (step 8), after 7 days of `password_reset` on the service |

## Residual risks

- **MailRelay's 24 h key window.** If the service is down for more than a day after MailRelay accepted a send but before the commit, a repeated send could slip past the window. Mitigation: alert on service backlog older than 12 h.
- **Personal data on the broker.** `email` and `payload` travel in the message. The broker is already shared with billing and search, so apply the same access controls.
- **Clock skew.** The latency gate compares timestamps from two services. Keep NTP healthy and alarm on skew.
- **`sent` overriding `failed` on a split outcome.** This case (old worker and service disagree) is rare and needs manual reconciliation after the page.

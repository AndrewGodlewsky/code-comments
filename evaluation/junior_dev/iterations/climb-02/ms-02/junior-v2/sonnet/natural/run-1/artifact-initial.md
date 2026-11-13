# Plan: extract notifications into a Notification Service

## How the pieces fit

**Callers do not change.** `enqueue_notification(tx, ...)` still inserts a `pending` row into the monolith's `notifications` table inside the caller's transaction. That row is the durable record, and the only way into the new path is through it.

**Components**

| Component | Lives in | Job |
|---|---|---|
| Old worker (`run_worker`) | monolith | Sends rows for types routed to `monolith`. Gets the `idempotency_key` fix and a flag filter. |
| Relay | monolith | Publishes `pending` rows of service-routed types to the broker, then marks them `handed_off`. |
| Result consumer | monolith | Applies `sent` / `failed` results from the service to the monolith row. |
| Notification Service | separate deploy and DB | Consumes requests, renders, sends, retries, pages, publishes results. |

**Row ownership, which is the core rule**

- A monolith row is `pending` (monolith owns it), `handed_off` (service owns it), or terminal (`sent` or `failed`).
- The route flag `notifications.route.<type>` (`monolith` or `service`) decides only where new `pending` rows go. It never moves a row that is already `handed_off`.
- The old worker never touches `handed_off` rows. The service never reads the flag. It finishes everything it has accepted, even after a rollback.
- Relay and old worker both claim rows with `FOR UPDATE SKIP LOCKED` and re-check `status = 'pending'`, so they cannot both take the same row, even during the 10 s flag skew between instances.

**Safety layers, strongest first**

1. Single ownership, as above.
2. Service-side dedupe: the service DB has a primary key on the notification `id`.
3. `idempotency_key = notification id` on every MailRelay send. This covers the one gap where ownership is ambiguous, which is a relay crash after the broker confirmed but before the row was marked `handed_off`. It also covers a crash after MailRelay accepted but before the state was committed. MailRelay's dedupe window is 24 h, so every alert below is set well inside it.

**Messages** (the broker is the only channel)

- `notifications.requested` carries `{id, type, user_id, email, payload, created_at, schema_version}`. The payload must be self-contained, because the service cannot read the monolith DB.
- `notifications.result` carries `{id, outcome: sent|failed, attempts, finished_at}`.

---

## Steps, in shipping order

### Step 1. Old worker sends with `idempotency_key`

- **Starts:** a normal monolith deploy. It has no dependency on anything else, and it also fixes the roughly 30 duplicate emails a week today.
- **Data moves:** `_deliver` calls `mailrelay.send(..., idempotency_key=row.id)`. The commit stays per batch.
- **State lives:** unchanged, in the monolith `notifications` table.
- **On failure:**
  - If an instance dies after MailRelay accepted some of a batch, those rows stay `pending` and are re-sent with the same key. MailRelay drops the repeat and returns success, so the row is marked `sent` with no second email.
  - A MailRelay timeout where the send actually succeeded behaves the same way on retry.
  - MailRelay down is handled exactly as today: attempts count up, and the row is marked `failed` and paged at attempt 5.
- **Caveat:** a row sent without a key before this deploy and re-sent after it can still duplicate once. This is a one-time transient.
- **Exit:** duplicate-email reports fall to about 0 over a week. The next steps do not need to wait for that.

### Step 2. Additive monolith changes: new status, route flags, worker filter

- **Starts:** a monolith deploy after step 1.
- **Data moves:**
  - Add status value `handed_off` and nullable columns `handed_off_at` and `result_at`.
  - Create flags `notifications.route.shipping_update`, `.order_confirmed` and `.password_reset`, all defaulting to `monolith`.
  - The worker query gains `AND type IN (types currently routed to monolith)`.
- **State lives:** the monolith DB and the flag system.
- **On failure:**
  - With every flag at `monolith`, behavior is identical to today, so there is nothing new to fail.
  - **Rollout gate:** no flag may be flipped until every monolith instance runs this version. An older instance has no filter and would send service-routed rows. The key would still stop a duplicate, but we do not rely on that. Verify the version on all instances.

### Step 3. Build and deploy the Notification Service with no traffic

- **Starts:** a separate deploy with its own database. It is not connected to production traffic yet.
- **Service DB table `notifications`:** `id` (PK), `type`, `user_id`, `email`, `payload`, `created_at` (the monolith's timestamp, used for latency), `status` (`pending|sent|failed`), `attempts`, `next_attempt_at`, `lease_until`, `accepted_at`, `result_published_at`, `page_pending`.
- **Consumer rule:**
  1. Insert with `ON CONFLICT (id) DO NOTHING` and commit.
  2. Only then ack the message.
  3. If the row already exists, ack. If that row is terminal and its result is unpublished or may be lost, queue the result to be republished.
- **Worker rule, same policy as today:**
  1. Claim a row with `status='pending' AND next_attempt_at <= now()` using `FOR UPDATE SKIP LOCKED`, and set `lease_until = now() + 60 s`. The claim commits immediately.
  2. Render the template, then call `mailrelay.send(..., idempotency_key=id)` outside any DB transaction.
  3. On success, set `status='sent'`, `attempts+1`, `accepted_at`, and commit per row (not per batch).
  4. On `mailrelay.Error`, `attempts = n`. If `n >= 5`, set `failed` and `page_pending=true` in one transaction. Otherwise set `next_attempt_at = now() + [1,2,4,8][n-1] min`.
  - A render error is not a MailRelay error and retrying cannot fix it. It goes straight to `failed` plus `page_pending`, and the same page applies. The old code would crash and replay the whole batch forever, so this is a deliberate difference. Confirm it with the team.
- **Result and page outboxes:**
  - A publisher sends `notifications.result` for terminal rows where `result_published_at IS NULL`. It sets that column after the broker confirms.
  - A pager loop calls `alerts.page_oncall` for rows with `page_pending=true`, then clears the flag. This guarantees "failed means paged". A crash between paging and clearing can page twice, which is acceptable because it is a duplicate page, not a duplicate email.
- **Wake-up:** the worker wakes immediately after a consumer insert and also polls every 1 s, so password reset latency is not bounded by a 5 s poll.
- **Template parity:** copy the three templates into the service and run golden-output tests against the monolith renderer using real payload samples.
- **On failure:**
  - **Service crash:** a message that was inserted but not acked is redelivered after 30 s and hits the PK, so there is no duplicate. A row mid-send has its lease expire and is re-claimed. The send repeats with the same key, so MailRelay returns success.
  - **Service DB down:** the consumer cannot commit, so it does not ack, and the broker redelivers.
  - **MailRelay down:** rows back off and fail per policy, and on-call is paged at attempt 5.
  - **Broker down:** results queue in the service DB and publish when it recovers.
  - **Redelivery to a second consumer while the first is still working:** the PK guarantees exactly one row.

### Step 4. Add the relay, result consumer and reconciler to the monolith (dark)

- **Starts:** a monolith deploy after step 3. With every flag at `monolith` the relay finds no rows, so nothing changes in production.
- **Relay, polling every 1 s:**
  1. In one transaction, select `pending` rows of service-routed types using `FOR UPDATE SKIP LOCKED`.
  2. Publish each to `notifications.requested` and wait for the broker's store confirmation.
  3. Set `status='handed_off', handed_off_at=now()` and commit.
  - Publishing happens while the row lock is held.
- **Result consumer:** `UPDATE notifications SET status=:outcome, result_at=now() WHERE id=:id AND status='handed_off'`, then ack. It does not page, because the service already did. A repeated result matches no row and is a no-op.
- **Reconciler:** a `handed_off` row with no result after 60 min is republished with the same `id`. The service dedupes, and if the row is terminal it re-emits the result. This recovers a lost result. It also raises a non-paging alert, because a long silence usually means the service is stuck.
- **State lives:** the monolith DB, which remains the first record of every notification.
- **On failure:**
  - **Broker down:** the publish fails or is unconfirmed. The row stays `pending`, the relay retries on the next poll, and nothing is lost. A backlog builds in the monolith DB, and an alert fires when the oldest service-routed `pending` row is older than 2 minutes.
  - **Relay crash after the broker confirmed but before the commit:** the row is still `pending` and gets republished. The service PK dedupes it. In a rollback this row could instead be sent by the old worker. The service may send it too, and the shared `idempotency_key` makes MailRelay drop the second send.
  - **Result consumer crash:** the message is not acked and is redelivered, and the update is idempotent.

### Step 5. Staging fault-injection gate

- **Starts:** all of step 4 is deployed. Nothing moves to production until this passes.
- **Data moves:** synthetic notifications against a MailRelay sandbox or stub that honors `idempotency_key`.
- **State lives:** staging copies of both DBs and the broker.
- **Drills, each of which must show zero lost and zero duplicate sends:**
  - Kill the relay after publish and before the mark.
  - Kill the service after the send and before the commit.
  - Redeliver every message twice, including concurrently to two consumers.
  - Take MailRelay down for 20 minutes and confirm the retry timing (1/2/4/8 minutes, then `failed` and paged).
  - Take the broker down and bring it back.
  - Flip the flag back mid-flight, as in the rollback drill below.
  - Deploy a template change.
- **On failure:** fix and re-run. Do not proceed to step 6.

### Step 6. Cut over `shipping_update` (day 0)

- **Starts:** the step 5 gate passes. An operator sets `notifications.route.shipping_update = service`. It takes effect on all monolith instances within 10 s.
- **Data moves:** from then on, new `shipping_update` rows (about 40,000 a day) go `pending` → relay → broker → service. Rows already `pending` at flip time are picked up by the relay on its next poll. Rows being sent by the old worker at the moment of the flip finish there.
- **State lives:** the monolith row records the handoff and the final result. The service DB holds attempts and backoff for everything it owns.
- **On failure:** see Rollback below. Any alert in the exit criteria is also a reason to roll back.
- **Exit criteria, at least 3 days:**
  - Zero notifications `pending` or `handed_off` for more than 30 min.
  - Zero duplicate-email reports.
  - Counts reconcile: monolith rows in the `shipping_update` group equal the service rows, and the `failed` counts match.
  - No unresolved reconciler alerts.

### Step 7. Cut over `order_confirmed` (day 3 or later)

- **Starts:** step 6 has met its exit criteria for at least 3 days. Flip `notifications.route.order_confirmed = service`.
- **Data moves:** about 12,000 a day through the same path.
- **State lives:** same as step 6.
- **Measuring latency, which is the gate for step 8:** the service records `accepted_at - created_at` for every notification and exports the p99. `created_at` is the monolith's timestamp and `accepted_at` is the service's, so keep NTP alert thresholds tight. Report two series: all accepted notifications, and first-attempt successes only. The first gives the requirement as written. The second tells us whether any miss is infrastructure or MailRelay retries, since the first retry already waits 60 s.
- **On failure:** same as step 6. A broker or service slowdown shows up as latency, so alert if the rolling p99 passes 45 s.
- **Exit criteria:** the same as step 6, for at least 3 days, plus p99 enqueue-to-MailRelay under 60 s on `order_confirmed`.

### Step 8. Cut over `password_reset` (day 6 or later)

- **Starts:** step 7 has run at least 3 days and the p99 gate is met. Both conditions are required. Flip `notifications.route.password_reset = service`.
- **Data moves:** about 1,500 a day. The requirement is p99 under 60 s, which the service now has to meet for this type.
- **State lives:** same as the earlier steps.
- **On failure:**
  - **Broker or service outage:** reset emails stop. The alert fires in 2 min. Roll back immediately by flipping the flag, since stale reset emails hurt users more than others.
  - **MailRelay down:** the same retry policy applies on either side.
- **Exit:** at least 7 days on the service with the p99 under 60 s, then go to step 9.

### Step 9. Decommission (day 13 or later)

- **Starts:** `password_reset` has run on the service for 7 days with the exit criteria met.
- **What changes:**
  - Remove `run_worker`, `_deliver` and the monolith template rendering.
  - Remove the route flags.
  - Keep `enqueue_notification`, the relay and the result consumer, because the relay is now the permanent handoff.
  - `pending` now means "waiting for the relay".
  - Drop the old worker's code path only after the last `pending` row sent by it has gone terminal.
- **State lives:** the monolith keeps the first record. The service DB holds all sending state.
- **On failure:** once the worker is gone, a flag flip can no longer roll back. Do this only after the 7-day period. If something fails afterward, redeploy the previous monolith release, whose old worker is still compatible with the schema.

---

## Rollback (valid until step 9)

**Procedure**

1. Set the type's route flag back to `monolith`. It takes effect on every instance within 10 s, well inside the one-minute requirement.
2. New and still-`pending` rows go to the old worker.
3. Rows already `handed_off` are not moved. The service finishes them (send, retry, fail and page) and publishes results. Do not stop or drain the service until `handed_off` for that type reaches 0.

**Why nothing is lost or re-sent**

- Each row is owned by exactly one side at any moment.
- The flag skew window is covered by row locks and the status re-check.
- The only ambiguous case is the relay crash gap, and `idempotency_key` covers it.

**If the service itself is dead (break-glass, not a flag flip)**

- Wait until the service recovers if possible. Its rows are safe in its DB and the broker.
- If it cannot recover within an hour, an operator may reset specific `handed_off` rows younger than 12 h back to `pending`. The old worker then sends them with the same key.
- This stays safe while the original handoff is within MailRelay's 24 h window. After that it can duplicate, so older rows must wait for the service.

**Rollback drill:** step 5 includes flipping the flag mid-flight with thousands of rows in each state. The result must be zero lost and zero duplicate emails.

---

## Earliest timeline

| Day | Event |
|---|---|
| Before 0 | Steps 1-5 |
| 0 | Step 6, `shipping_update` moves |
| 3 or later | Step 7, `order_confirmed` moves |
| 6 or later | Step 8, `password_reset` moves (needs the p99 gate) |
| 13 or later | Step 9, remove the old worker |

---

## Open questions

1. Is the render-error behavior in step 3 acceptable? Today a bad payload would crash and replay the batch forever.
2. Does the p99 requirement include notifications delayed by a MailRelay retry (all accepted, the stricter reading), or only first-attempt successes? The plan reports both, and the gate uses the all-accepted series unless told otherwise.
3. Is carrying the recipient email in broker messages acceptable? Billing and search already use this broker, but we have not confirmed its data policy.

# Plan: extract notifications into a Notification Service

## How the pieces fit

**Callers do not change.** `enqueue_notification(tx, ...)` still inserts a `pending` row into the monolith's `notifications` table inside the caller's transaction. That row is the durable record, and the only way into the new path.

| Component | Lives in | Job |
|---|---|---|
| Old worker (`run_worker`) | monolith | Sends rows of types routed to `monolith`. Gets the `idempotency_key` fix and a type filter. |
| Relay | monolith | Publishes `pending` rows of service-routed types to the broker, then marks them `handed_off`. |
| Result consumer | monolith | Applies `sent` / `failed` results from the service to the monolith row. |
| Reconciler | monolith, in the relay's loop | Republishes `handed_off` rows that have no result for too long. |
| Notification Service | separate deploy and DB | Consumes requests, renders, sends, retries, pages, publishes results. |

**Row ownership (the core rule)**

- A monolith row is `pending` (monolith owns it), `handed_off` (service owns it), or terminal (`sent` or `failed`).
- The flag `notifications.route.<type>` (`monolith` or `service`) decides only where `pending` rows go. It never moves a `handed_off` row.
- The old worker and the relay read the flag on every poll, so the platform's 10 s propagation is the only skew. Both claim rows with `FOR UPDATE SKIP LOCKED` and re-check `status = 'pending'`, so they cannot take the same row.
- The old worker never touches `handed_off` rows. The service never reads the flag and finishes everything it accepted, even after a rollback.
- A monolith `failed` status is only a record. The service has already paged on-call.

**Duplicate protection**

1. Single ownership, as above.
2. The service DB has a primary key on the notification `id`, so redelivered requests dedupe.
3. `idempotency_key = notification id` on every MailRelay send. This covers the one ambiguous case (relay crash after the broker confirmed but before the row was marked `handed_off`), a crash after MailRelay accepted but before commit, and a lease that expires during a slow send. MailRelay's window is 24 h, so every alert below is set well inside it.

**Messages** (the broker is the only channel; a message not acked within 30 s is redelivered)

- `notifications.requested`: `{id, type, user_id, email, payload, created_at, schema_version}`. Self-contained, because the service cannot read the monolith DB.
- `notifications.result`: `{id, outcome: sent|failed, attempts, finished_at}`.

---

## Steps, in shipping order

### Step 1. Old worker sends with `idempotency_key`

- **Starts:** a normal monolith deploy. It depends on nothing and also fixes today's roughly 30 duplicate emails a week.
- **Data moves:** `_deliver` calls `mailrelay.send(..., idempotency_key=row.id)`. Commit stays per batch.
- **State lives:** unchanged, in the monolith table.
- **On failure:** if an instance dies after MailRelay accepted part of a batch, the rows stay `pending` and are re-sent with the same key. MailRelay drops the repeat and returns success, so the row becomes `sent` with no second email. A timeout where the send actually succeeded behaves the same. MailRelay down is handled as today (retries, then `failed` and paged at attempt 5).
- **Caveat:** a row sent without a key before this deploy and re-sent after it can duplicate once.

### Step 2. Additive monolith changes

- **Starts:** a monolith deploy after step 1.
- **Data moves:**
  - Add status `handed_off` and nullable columns `handed_off_at` and `result_at`.
  - Create flags `notifications.route.shipping_update`, `.order_confirmed`, `.password_reset`, all defaulting to `monolith`.
  - The worker query gains `AND type IN (types currently routed to monolith)`.
- **State lives:** the monolith DB and the flag system.
- **On failure:** with every flag at `monolith`, behavior is identical to today. **Gate:** flip no flag until every monolith instance runs this version, because an older instance has no filter and would send service-routed rows.

### Step 3. Build and deploy the Notification Service with no traffic

- **Starts:** a separate deploy with its own DB, not connected to production traffic.
- **Service table `notifications`:** `id` (PK), `type`, `user_id`, `email`, `payload`, `created_at` (the monolith's timestamp, used for latency), `status` (`pending|sent|failed`), `attempts`, `next_attempt_at`, `lease_until`, `accepted_at`, `result_published_at`, `page_pending`.
- **Consumer rule:** insert with `ON CONFLICT (id) DO NOTHING`, commit, then ack. If the row already exists, ack; if it is terminal, queue its result for republishing.
- **Worker rule (same retry policy as today):**
  1. Claim a row with `status='pending' AND next_attempt_at <= now()` using `FOR UPDATE SKIP LOCKED`, set `lease_until = now() + 60 s`, and commit immediately.
  2. Render, then call `mailrelay.send(..., idempotency_key=id)` outside any DB transaction.
  3. On success, set `status='sent'`, `attempts+1`, `accepted_at`, committing per row.
  4. On `mailrelay.Error`, with `n` attempts: if `n >= 5`, set `failed` and `page_pending=true` in one transaction; otherwise set `next_attempt_at = now() + [1,2,4,8][n-1] min`.
  5. Every update is guarded by `WHERE id=:id AND status='pending' AND lease_until=:my_lease`, so a late worker whose lease was taken over matches no row.
  - Two workers may both send a row if a lease expires mid-send. This is safe because the key is the same.
  - A render error cannot be fixed by retrying, so it goes straight to `failed` plus `page_pending`. The old code would crash and replay the batch forever, so this is a deliberate difference (see open question 1).
- **Result and page outboxes:** a publisher sends `notifications.result` for terminal rows with `result_published_at IS NULL` and sets that column after the broker confirms. A pager loop calls `alerts.page_oncall` for rows with `page_pending=true`, then clears the flag. A crash in between can page twice, which is acceptable.
- **Latency:** the worker polls every 1 s and wakes right after a consumer insert, so password reset is not held back by a 5 s poll.
- **Template parity:** copy the three templates into the service and run golden-output tests against the monolith renderer on real payload samples.
- **On failure:**
  - **Service crash:** an inserted but unacked message is redelivered and hits the PK. A row mid-send has its lease expire and is re-claimed, and the repeat send carries the same key.
  - **Service DB down:** the consumer cannot commit, so it does not ack and the broker redelivers.
  - **MailRelay down:** retry and fail per policy, paging at attempt 5.
  - **Broker down:** results wait in the service DB and publish on recovery.
  - **Redelivery to a second consumer:** the PK keeps exactly one row.

### Step 4. Add relay, result consumer, reconciler and dashboards to the monolith (dark)

- **Starts:** a monolith deploy after step 3. With every flag at `monolith` the relay finds no rows, so nothing changes.
- **Relay** (polls every 1 s, up to 50 rows per batch):
  1. In one transaction, select `pending` rows of service-routed types with `FOR UPDATE SKIP LOCKED`.
  2. Publish each to `notifications.requested` and wait for the broker's store confirmation.
  3. Set `status='handed_off', handed_off_at=now()` for the confirmed rows and commit.
  - Unconfirmed rows stay `pending` and are retried on the next poll without blocking the others.
- **Result consumer:** `UPDATE notifications SET status=:outcome, result_at=now() WHERE id=:id AND status='handed_off'`, then ack. It does not page. A repeated or stale result matches no row.
- **Reconciler:** every minute, republish (same `id`, status unchanged) any `handed_off` row with no result after 60 min, which is well past the roughly 15 min of service retries. The service dedupes, and re-emits the result if its row is terminal. It also raises a non-paging alert, since long silence usually means the service is stuck.
- **Dashboards and alerts:** per type, counts of `pending`, `handed_off` and `failed` rows with the age of the oldest of each, and the reconciler alert. The service exports matching counts. Operators compare the two sides by eye, because the DBs cannot be joined.
- **State lives:** the monolith DB remains the first record.
- **On failure:**
  - **Broker down:** rows stay `pending`, the relay retries, and a backlog builds in the monolith. Alert when the oldest service-routed `pending` row is older than 2 minutes.
  - **Relay crash after the broker confirmed but before the commit:** the row is still `pending` and is republished, and the service PK dedupes it. After a rollback the old worker might send it as well, and the shared key makes MailRelay drop the second send.
  - **Result consumer crash:** the message is redelivered and the update is idempotent.

### Step 5. Staging fault-injection gate

- **Starts:** step 4 is deployed. Nothing moves to production until this passes.
- **Data moves:** synthetic notifications against a MailRelay stub that honors `idempotency_key`. State lives in staging copies of both DBs and the broker.
- **Drills, each requiring zero lost and zero duplicate sends:**
  - Kill the relay after publish and before the mark.
  - Kill the service after the send and before the commit.
  - Redeliver every message twice, including concurrently to two consumers.
  - Take MailRelay down for 20 minutes and confirm the 1/2/4/8 minute timing, then `failed` and paged.
  - Take the broker down and bring it back.
  - Flip the flag back mid-flight with thousands of rows in each state.
  - Deploy a template change.
- **On failure:** fix and re-run. Do not proceed.

### Step 6. Cut over `shipping_update` (day 0)

- **Starts:** the step 5 gate passes and an operator sets `notifications.route.shipping_update = service`, effective on all monolith instances within 10 s.
- **Data moves:** new rows (about 40,000 a day) go `pending` → relay → broker → service. Rows already `pending` at flip time are picked up by the relay. Rows the old worker is already sending finish there.
- **State lives:** the monolith row records the handoff and final result. The service DB holds attempts and backoff.
- **On failure:** roll back (see Rollback). Any missed exit criterion is also a reason to roll back.
- **Exit criteria, for at least 3 days, read from the step 4 dashboards:**
  - No notification `pending` or `handed_off` for more than 30 min.
  - No duplicate-email reports.
  - Monolith and service counts reconcile, including `failed`.
  - No unresolved reconciler alerts.

### Step 7. Cut over `order_confirmed` (day 3 or later)

- **Starts:** step 6 met its exit criteria for at least 3 days. Flip `notifications.route.order_confirmed = service`.
- **Data moves:** about 12,000 a day through the same path. State lives as in step 6.
- **Latency gate for step 8:** the service records `accepted_at - created_at` for every notification and exports the p99. The two timestamps come from different clocks, so keep NTP alert thresholds tight. Report two series: all accepted notifications (the requirement as written), and first-attempt successes only (to separate infrastructure delay from MailRelay retries, since the first retry already waits 60 s).
- **On failure:** as in step 6. Also alert if the rolling p99 passes 45 s.
- **Exit criteria:** those of step 6 for at least 3 days, plus p99 enqueue-to-MailRelay under 60 s.

### Step 8. Cut over `password_reset` (day 6 or later)

- **Starts:** step 7 has run at least 3 days and the p99 gate is met (both are required). Flip `notifications.route.password_reset = service`.
- **Data moves:** about 1,500 a day, and the service must now meet p99 under 60 s for this type.
- **On failure:** a broker or service outage stops reset emails and the 2 minute alert fires. Roll back at once by flipping the flag. MailRelay down follows the same retry policy on either side.
- **Exit:** at least 7 days on the service with p99 under 60 s.

### Step 9. Decommission (day 13 or later)

- **Starts:** `password_reset` has run on the service for 7 days with the exit criteria met.
- **What changes:**
  - Remove `run_worker`, `_deliver`, the monolith template rendering and the route flags, but only after the last row the old worker owned has gone terminal.
  - Keep `enqueue_notification`, the relay and the result consumer. `pending` now means "waiting for the relay".
- **State lives:** the monolith keeps the first record. The service DB holds all sending state.
- **On failure:** a flag flip can no longer roll back. Redeploy the previous monolith release, whose old worker is compatible with the schema.

---

## Rollback (valid until step 9)

1. Set the type's route flag back to `monolith`. It takes effect on every instance within 10 s, inside the one-minute requirement.
2. New and still-`pending` rows go to the old worker.
3. Rows already `handed_off` stay with the service, which finishes them (send, retry, fail, page) and publishes results. Do not stop the service until `handed_off` for that type reaches 0.

Nothing is lost or re-sent because each row has exactly one owner, row locks plus the status re-check cover the flag skew, and `idempotency_key` covers the one ambiguous case, the relay crash gap.

---

## Open questions

1. Is the render-error behavior in step 3 acceptable? Today a bad payload would crash and replay the batch forever.
2. Does the p99 requirement include notifications delayed by a MailRelay retry? The plan reports both series and gates on the all-accepted one unless told otherwise.
3. Is carrying the recipient email in broker messages acceptable? Billing and search use this broker, but its data policy is unconfirmed.
4. Which broker product is it, and do consumers push or pull? The plan does not depend on it, but the service's consumer code does.
5. What is MailRelay's send timeout? It should stay well under the 60 s lease.

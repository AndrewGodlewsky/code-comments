# Plan: Extract notifications into a Notification Service

## How it works

**Ownership.** At any moment a notification belongs to exactly one sender. The monolith row's `status` records who:

| Row status (monolith) | Owner |
|---|---|
| `pending` | The monolith's old worker. The relay may also claim it if its type is routed to the service. |
| `handed_off` | The service. The monolith never sends it. |
| `sent` / `failed` | Nobody. The row is terminal. |

**Routing.** There is one flag per type, `notifications.route.<type>`, with value `monolith` (the default) or `service`. The flag only decides which side claims **new `pending` rows**. It never takes a row away from the side that already owns it.

**Handoff.** An outbox relay in the monolith reads `pending` rows of service-routed types, publishes them to the broker, and flips them to `handed_off` after the broker confirms. The row's id is the broker message id and the service's primary key.

**Reporting back.** The service sends results back over a second broker topic. These results only mirror status into the monolith table. Delivery does not depend on them.

**Two layers prevent duplicates.**
1. Exclusive ownership prevents them by construction.
2. Passing the notification id as MailRelay's `idempotency_key` is the backstop. It covers a crash after MailRelay accepted a send but before the sender recorded it.

**Assumptions to confirm before step 3:**
- `templates.render(type, payload)` needs nothing beyond `type` and `payload`.
- The broker retains unconsumed messages for longer than the longest service outage we plan to ride out.
- The service has its own on-call paging path.

## Timeline

| Step | Earliest start | Gate |
|---|---|---|
| 1. Idempotency key on old worker | Day 0 | Duplicate-email tickets fall |
| 2. Monolith groundwork (dark) | After 1 | All instances on the new build |
| 3. Build and deploy service (dark) | Parallel with 2 | Staging end-to-end passes |
| 4. Relay and result consumer (dark) | After 2 and 3 | Staging and production dry run |
| 5. Move `shipping_update` | After 1 to 4 | None |
| 6. Rollback drill | During the first days of 5 | No duplicates, no losses |
| 7. Move `order_confirmed` | At least 3 days after the last `shipping_update` flip to `service` | Stable on service |
| 8. Latency gate | At least 3 days of `order_confirmed` | p99 under 60 s |
| 9. Move `password_reset` | After 8 | Gate met |
| 10. Decommission | At least 7 days after 9 | Zero old-worker work remaining |

---

## 1. Pass `idempotency_key` from the old worker

**Starts it:** A merge and deploy. It goes first, before anything else exists. No type may move until it has been live everywhere.

**Change:** In `_deliver`, call `mailrelay.send(to=..., subject=..., body=..., idempotency_key=row.id)`. Nothing else changes: same batching, retries and statuses.

**Data moves:** The notification id goes to MailRelay as the key. Nothing else moves.

**State:** Unchanged, in the monolith `notifications` table. MailRelay remembers keys for 24 hours.

**Failures:**
- **Instance dies after MailRelay accepted a send but before the batch commit (today's ~30 duplicates a week).** The rows stay `pending` and are retried with the same key. MailRelay drops the repeat and returns success, and the row is marked `sent`. The duplicate is gone.
- **MailRelay times out but had actually accepted the send.** The retry reuses the key and returns success. No duplicate.
- **MailRelay down.** Unchanged. The retries are 1, 2, 4 and 8 minutes, then `failed` and a page.
- **Limit.** The key only protects repeats within 24 hours. Our whole retry window is 15 minutes, so this only matters for outages far longer than that. Every later step relies on the same 24-hour assumption.

**Verify:** Duplicate-email support tickets drop to roughly zero over a week. MailRelay's drop count is not visible to us because it returns success, so tickets are the signal.

---

## 2. Monolith groundwork, dark

**Starts it:** Deploy after step 1. All changes are inert until a flag flips.

**Changes:**
- **Schema (additive):** allow `status = 'handed_off'` and add `handed_off_at timestamptz`.
- **Flags:** create `notifications.route.shipping_update`, `.order_confirmed` and `.password_reset`, all defaulting to `monolith`.
- **Old worker:** each loop iteration reads the flags and adds `AND type NOT IN (<types routed to service>)` to its `SELECT`. Nothing else in `run_worker` or `_deliver` changes.

**Data moves:** None.

**State:** Monolith database and flags.

**Failures:**
- **Mixed versions during rollout.** An old-build instance has no filter, so it would keep sending a type that has been flipped to `service`. That is the main danger of this step. No flag may flip until every monolith instance reports the new build. The check is a build-version metric per instance, not an assumption.
- **Flag read fails.** The worker treats an unreadable flag as `monolith`, its safe default.

---

## 3. Build and deploy the Notification Service, dark

**Starts it:** Developed in parallel with step 2. Deployed separately from the monolith with its own database, and no traffic.

**Service database:**
- `notifications`:
  - `id` (PRIMARY KEY, the monolith id)
  - `type`, `user_id`, `email`, `payload`
  - `created_at` (the monolith's original value)
  - `received_at`
  - `status` (`pending`, `sent` or `failed`)
  - `attempts`, `next_attempt_at`
  - `lease_until`, `sent_at`, `paged_at`
- `result_outbox`: `id`, `notification_id`, `status`, `attempts`, `published_at`

**Components:**
- **Consumer** on topic `notifications.send`.
- **Sender** loop.
- **Result publisher** on topic `notifications.result`.
- **Failure pager.**

**Consumer behaviour.** For each message:
1. In one transaction, run `INSERT ... ON CONFLICT (id) DO NOTHING`. The row keeps the message's `attempts` and `next_attempt_at`, so a retry that started on the monolith continues with the same schedule.
2. Commit.
3. Only then acknowledge.

The consumer never acknowledges after a MailRelay call. That keeps every ack well inside the broker's 30 s window even when MailRelay is slow.

**Sender behaviour.** It runs the same policy as today:
1. **Claim:** `UPDATE ... SET lease_until = now() + 60s WHERE id IN (SELECT ... WHERE status='pending' AND next_attempt_at <= now() AND (lease_until IS NULL OR lease_until < now()) ORDER BY created_at LIMIT 50 FOR UPDATE SKIP LOCKED)`. This commits before any send. The lease must exceed MailRelay's timeout.
2. **Render and send:** render the template, then call `send(..., idempotency_key=id)`.
3. **Record the result per row** in its own short transaction, together with its `result_outbox` row:
   - **Success:** `sent`, `attempts + 1`.
   - **`mailrelay.Error` or a render error, attempts below 5:** set `attempts + 1` and `next_attempt_at = now() + [1,2,4,8][attempts-1]` minutes.
   - **`mailrelay.Error` or a render error, attempts reach 5:** `failed`.

A claim does not consume an attempt, so a crash during a send matches today's behaviour. The only difference from today is that a render error counts as a failed attempt. Today it would crash the whole batch forever.

**Failure pager.** Failed rows with `paged_at IS NULL` are paged, then stamped. The stamp happens after the page, so a crash between the two causes a second page but never a missed one.

**Result publisher.** It publishes unpublished `result_outbox` rows with broker confirmation, then marks them published. It is at-least-once.

**Data moves:** Nothing flows between systems yet.

**State:** Entirely in the service database.

**Failures:**
- **Service crashes after MailRelay accepts a send but before the row is updated.** The lease expires and the row is re-claimed. It is re-sent with the same key, MailRelay returns success, and the row becomes `sent`. This works inside the 24 h window.
- **Redelivered message.** The primary-key conflict makes it a no-op, and it is acknowledged. An already-`sent` row is never sent again.
- **MailRelay down.** Rows retry on the 1/2/4/8 schedule, then go `failed` with a page. Nothing waits on an ack.
- **Service database down.** The consumer cannot insert, so it does not ack. The broker redelivers after 30 s.

**Verify:** In staging, send synthetic notifications to the MailRelay sandbox, covering success, MailRelay errors, a crash between send and record, and a duplicated message.

---

## 4. Monolith relay and result consumer, dark

**Starts it:** Deploy after steps 2 and 3. With all flags on `monolith` the relay finds no rows.

**Relay.** Runs as a background thread alongside the worker. Each pass, with a poll interval of 1 s:
1. In one transaction, select `pending` rows of service-routed types `FOR UPDATE SKIP LOCKED`, up to 100.
2. Publish each to `notifications.send` with message id = notification id. The message carries `id`, `type`, `user_id`, `email`, `payload`, `created_at`, `attempts` and `next_attempt_at`. A row that is mid-retry has its retry state carried over, so the service continues the schedule.
3. Wait for the broker's confirmation of every message. Time out after 5 s and roll back.
4. Set `status = 'handed_off'`, `handed_off_at = now()`, and commit.

**Result consumer.** It reads `notifications.result` and runs `UPDATE notifications SET status = :s, attempts = :a WHERE id = :id AND status = 'handed_off'`. It acks after the commit. The row mirrors the outcome and is never re-sent. The service owns the page, so the monolith does not page again.

**Staleness alarm.** Alert if any `handed_off` row is older than 30 minutes with no result. The full retry cycle takes about 15 minutes. The alarm only detects a stall. It never re-sends anything.

**Data moves:** Rows go out in messages and results come back as messages. Neither side touches the other's database.

**State:** The monolith table holds the durable record. The broker holds only in-transit copies.

**Failures:**
- **Broker down.** Publish or confirmation fails, the transaction rolls back, and the rows stay `pending`. They are retried every second. `enqueue_notification` is unaffected, since it only inserts a row. Checkout keeps working.
- **Relay crashes after the broker confirmed but before the commit.** The row stays `pending` and is re-published on the next pass. The service ignores the second copy because the id is its primary key.
- **Broker redelivers a result.** The `status = 'handed_off'` guard makes it a no-op.
- **Row locked by the old worker.** `SKIP LOCKED` skips it. The relay takes it next pass if it is still `pending`.
- **Lost message.** The staleness alarm fires. See step 6 for recovery.

---

## 5. Move `shipping_update`

**Starts it:** Setting `notifications.route.shipping_update = service`. It reaches every instance within 10 s. Preconditions: steps 1 to 4 are done and every instance runs the new build.

**Flow:**
1. A carrier webhook runs `enqueue_notification(tx, ...)`, which is unchanged. The row is `pending`.
2. The old worker now excludes this type. The relay publishes the row and marks it `handed_off`.
3. The service consumer stores it and acks.
4. The sender renders the template, sends with the key, and records `sent`.
5. The result event arrives and the monolith row becomes `sent`.

**Rows in flight at the flip:**
- A `pending` row, including one mid-retry, is claimed under a row lock by exactly one of the worker or the relay. Instances may disagree on the flag for up to 10 s. The lock decides who claims, and the loser skips the row.
- If the worker has sent a row but not yet committed, the relay's `SKIP LOCKED` skips it until the commit lands.
- If the worker crashes before that commit, the row stays `pending` and may go to the service later. This is the crash-after-send case. The service re-sends with the same key and MailRelay drops it.

**Data moves:** The notification payload, one message per notification, goes to the service. The result goes back.

**State:** The monolith row is the durable origin. After handoff, the service's `notifications` row is the source of truth for the send.

**Failures:**
- **MailRelay down.** The service retries on its own, 5 attempts over 15 minutes, then marks `failed` and pages. The monolith row mirrors `failed`.
- **Service crash or restart.** Leases expire and rows are re-claimed. Messages not yet consumed wait in the broker.
- **Broker down.** The monolith holds rows as `pending` and the relay catches up afterwards. Already `handed_off` rows keep sending in the service.
- **Service down for a long time.** Messages wait in the broker and the staleness alarm fires.

**Gate:** At least 3 days on the service, counted from the last flip to `service` (see step 6), before step 7. Watch send success rate, backlog, and p50/p99 enqueue-to-MailRelay time.

---

## 6. Rollback drill, and the rollback rule for every type

**Starts it:** In the first day or two after step 5, flip `notifications.route.shipping_update = monolith` in a quiet period. Watch for 15 minutes, then flip it back to `service`. The 3-day soak in step 5 restarts from this last flip.

**What rollback does:** Within 10 s of the flip, the old worker starts claiming new `pending` rows of that type. Within about 15 s in total, the relay stops claiming them.

**In-flight rows are not moved:**
- Rows that are already `handed_off` stay with the service and are finished there, with the same 5-attempt policy.
- Rows still `pending` are claimed by whichever side takes them first, and exactly one does.
- Nothing is re-sent, because ownership never changes after a row leaves `pending`. The idempotency key covers the one crash case.

**Result:** Rollback is one flag flip, takes effect inside a minute, loses nothing and re-sends nothing.

**Rollback when the service itself is broken (break-glass):**
- **The problem.** `handed_off` rows are stuck, because the monolith will not touch them.
- **Before anything else.** Pause the service consumer and sender for that type with the service's own switch, and let the result consumer drain.
- **Safe to reclaim:** rows with `created_at` under 24 hours old and still `handed_off`. They are set back to `pending` by an operator, and the old worker sends them with the same key. If the service sent one just before the pause, MailRelay drops the repeat, because the key is still within 24 hours.
- **Not safe to reclaim:** `handed_off` rows older than 24 hours, because the key has expired. Review those manually.
- **Known gap.** Reclaimed rows restart at `attempts = 0`, which gives them slightly more than 5 attempts overall. This path is only for an incident and is not part of normal rollback.

**Verify during the drill:** Zero duplicate emails. Every row created during the drill ends `sent` or `failed`. The `handed_off` rows finish on the service.

---

## 7. Move `order_confirmed`

**Starts it:** At least 3 days after the last `shipping_update` flip to `service`, and nothing from step 5 or 6 is failing. Flip `notifications.route.order_confirmed = service`.

**Flow, data and state:** Identical to step 5. Volume is 12,000 a day. The trigger is checkout committing an order.

**Failures:** Same as step 5. A broker or service problem at this point does not affect checkout. Enqueue is a local insert, and the relay catches up afterwards.

**Rollback:** As in step 6. The flag is flipped back and the type returns to the monolith with no loss or duplicates.

**Gate:** At least 3 days on the service, then step 8.

---

## 8. Latency gate for `password_reset`

**Starts it:** At the end of `order_confirmed`'s 3 days on the service.

**What is measured:**
- **Metric.** For `order_confirmed`, the service records `sent_at - created_at`, where `created_at` is the monolith row's creation time carried in the message. This is enqueue-to-MailRelay.
- **Pass condition.** Over the whole 3-day window, p99 is under 60 s. All sends count, including retried ones. At about 12,000 a day that is about 36,000 samples, which is enough for p99.
- **Diagnostics.** Also record the first-attempt-only distribution, to tell "pipeline slow" from "MailRelay incidents with retries".
- **If it fails.** Do not move `password_reset`. Fix the cause and restart the 3-day measurement.

**Expected budget:** Relay poll 1 s, publish and confirm well under 1 s, consume and insert under 1 s, sender poll 1 s, MailRelay call. That leaves a lot of headroom under 60 s.

**Data and state:** The service holds the timestamps. Nothing else moves.

---

## 9. Move `password_reset`

**Starts it:** Step 8 passes. Flip `notifications.route.password_reset = service`.

**Flow, data, state and failures:** As in step 5. The 60 s requirement is a standing alert, for example p99 above 30 s over 15 minutes. If the alert fires, the first response is the step 6 flag flip back to `monolith`.

**Rollback:** As in step 6. It matters most here, because users are waiting.

**Gate:** The service has run `password_reset` for 7 days with no rollback. Counting restarts on any flip back.

---

## 10. Decommission the old worker

**Starts it:** `password_reset` has run on the service for 7 days with p99 under 60 s.

**Sequence:**
1. **Pre-checks.**
   - No `pending` rows exist for any type.
   - No `handed_off` rows are older than 30 minutes.
   - Both the worker and relay queues are empty.
2. **Stop the worker.** Deploy with `run_worker` not started. The relay, result consumer, `enqueue_notification` and the flags remain.
3. **Observe** for a day. Pending rows should be zero and sends continuing.
4. **Delete the old worker code** (`run_worker`, `_deliver`, the old backoff constants) and the worker filter from step 2.
5. **Later cleanup.** Retire the per-type flags in a separate change, once nobody needs rollback.

**State and data:** Unchanged. The service now does all sending.

**Failures:**
- **Service or broker down, with no old worker.** Rows accumulate as `pending` or `handed_off`. Checkout is unaffected, and delivery resumes on recovery.
- **Rollback after deletion.** There is no fallback sender any more. Recovery is a service fix, plus the break-glass procedure in step 6 only if a worker is redeployed from history.

---

## Summary of guarantees

| Scenario | Outcome |
|---|---|
| Caller's transaction rolls back | No row, no notification. |
| Monolith crash after MailRelay accepts (steps 1 to 4) | Retried with the same key. MailRelay drops the repeat. |
| Relay crash after broker confirm | The row is re-published. The service ignores the duplicate. |
| Broker redelivery to the service | Primary-key conflict, no-op, acknowledged. |
| Service crash after MailRelay accepts | The lease expires and the row is re-sent with the same key. MailRelay drops the repeat. |
| Redelivered result event | Guarded update, no-op. |
| MailRelay down | 5 attempts over 15 minutes, then `failed` with a page. |
| Broker down | The monolith holds `pending` rows. Checkout is unaffected. |
| Rollback flip | Within about 15 s. In-flight rows finish with their current owner. |

**Residual risk.** Duplicate protection leans on MailRelay's 24-hour key window for the crash cases. A crash combined with a delay of more than 24 hours could duplicate. The 30-minute staleness alarm and the 24-hour limit on reclaim keep that window from being reached in practice.

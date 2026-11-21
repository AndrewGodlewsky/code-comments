# Plan: Extract notifications into a Notification Service

## Summary

Today the monolith's own worker sends notifications. It reads `pending` rows from the monolith `notifications` table, renders them and calls MailRelay. This competes with checkout for CPU and database connections, and a crash can resend a batch (about 30 duplicate emails a week). We move sending into a separate Notification Service with its own database, one notification type at a time. The monolith keeps recording every notification first, then an outbox relay hands each row over through the broker. Every row has exactly one owner at any moment, and the notification id is MailRelay's `idempotency_key` as a backstop, so a notification is never sent twice and never lost.

## Terms

- **Monolith**: the existing application. Its `enqueue_notification(tx, ...)` inserts a `pending` row inside the caller's transaction (checkout, carrier webhook, password reset). Callers do not change.
- **Old worker**: `run_worker` and `_deliver` in `app/notifications.py`. Every monolith instance runs one. It claims `pending` rows with `FOR UPDATE SKIP LOCKED`, sends them, and commits once per batch of 50.
- **Notification Service**: the new, separately deployed sender. It has its own database. Neither system reads or writes the other's database.
- **Broker**: the message system already used by billing and search. It is the only channel between the monolith and the service. It is at-least-once. A message not acknowledged within 30 s is redelivered, possibly to another consumer. Publishers get a confirmation once a message is stored.
- **MailRelay**: the email provider. All three types are email only. With an `idempotency_key`, it drops a repeat of a send it accepted in the last 24 hours and returns success.
- **Flag**: a runtime setting read with `flags.get(name)`. A change reaches every monolith instance within 10 s.
- **Route flag**: `notifications.route.<type>`, with value `monolith` (default) or `service`. It decides only who claims new `pending` rows of that type.
- **Relay**: a new background thread in the monolith. It publishes `pending` rows of service-routed types to the broker, then marks them `handed_off`.
- **Lease**: a time-limited claim on a service row. If the sender dies, the lease expires and another claim can take the row.
- **Types**: `shipping_update` (40,000 a day), `order_confirmed` (12,000 a day) and `password_reset` (1,500 a day). `password_reset` has a requirement: p99 enqueue-to-MailRelay under 60 s.

## Rules that hold at every step

- **Retries**: 5 attempts, waits of 1, 2, 4 and 8 minutes before attempts 2 to 5, then mark `failed` and page on-call. This is the same on either side. The whole cycle takes about 15 minutes.
- **Nothing lost**: every notification whose enqueuing transaction committed ends up accepted by MailRelay, or `failed` with on-call paged.
- **Nothing duplicated**: not after a crash, a broker redelivery, a cutover or a rollback.
- **Rendering** moves into the service.
- **Ownership**: the monolith row's `status` says who owns it.

| Row status (monolith) | Owner |
|---|---|
| `pending` | The old worker. The relay may also claim it if its type is routed to the service. |
| `handed_off` | The service. The monolith never sends it. |
| `sent` / `failed` | Nobody. The row is terminal. |

Ownership never changes after a row leaves `pending`. A flag flip never takes a row from the side that already owns it. Two layers prevent duplicates: exclusive ownership prevents them by construction, and the idempotency key covers a crash after MailRelay accepted a send but before the sender recorded it.

## How it runs (after full cutover)

1. **Record.** Business code calls `enqueue_notification` in its transaction. The row is `pending` in the monolith table. This is the durable origin. If the caller rolls back, there is no row and no notification.
2. **Hand off.** Each second the relay does the following:
   1. In one transaction, select up to 100 `pending` rows of service-routed types `FOR UPDATE SKIP LOCKED`.
   2. Publish each to `notifications.send`, with message id equal to the notification id. The message carries `id`, `type`, `user_id`, `email`, `payload`, `created_at`, `attempts` and `next_attempt_at`. A row that is mid-retry keeps its retry state, so the service continues the schedule.
   3. Wait for the broker's confirmation of every message. Time out after 5 s and roll back.
   4. Set `status = 'handed_off'` and `handed_off_at = now()`, then commit.
3. **Store.** The service consumer, in one transaction, runs `INSERT ... ON CONFLICT (id) DO NOTHING` into the service `notifications` table, commits, and only then acknowledges. It never acknowledges after a MailRelay call, so every ack stays well inside the 30 s window. If the database is down it does not ack, and the broker redelivers.
4. **Send.** The sender loop does the following:
   1. **Claim**, committing before any send: set `lease_until = now() + 60s` on up to 50 rows where `status = 'pending'`, `next_attempt_at <= now()` and the lease is empty or expired, oldest `created_at` first, `FOR UPDATE SKIP LOCKED`. The lease must exceed MailRelay's timeout. A claim does not consume an attempt.
   2. **Render and send**: render the template, then call `send(..., idempotency_key=id)`.
   3. **Record** the result per row, in its own short transaction together with a `result_outbox` row:
      - Success: `sent`, `attempts + 1`.
      - `mailrelay.Error` (including timeouts) or a render error, below 5 attempts: `attempts + 1` and `next_attempt_at = now() + [1,2,4,8][attempts-1]` minutes.
      - The same errors when attempts reach 5: `failed`.
   
   Today a render error crashes the whole batch forever. In the service it counts as a failed attempt.
5. **Page.** The failure pager pages for failed rows with `paged_at IS NULL`, then stamps `paged_at`. A crash between the page and the stamp causes a second page, never a missed one. The service has its own on-call paging path, and the monolith does not page for handed-off rows.
6. **Report back.** The result publisher publishes unpublished `result_outbox` rows to `notifications.result` with broker confirmation, then marks them published. It is at-least-once. The monolith's result consumer runs `UPDATE notifications SET status = :s, attempts = :a WHERE id = :id AND status = 'handed_off'`, then acks after the commit. This only mirrors the outcome. Delivery does not depend on it.
7. **Alarm.** Alert if any `handed_off` row is older than 30 minutes with no result. The alarm only detects a stall. It never re-sends anything.

**Service database.**
- `notifications`: `id` (primary key, the monolith id), `type`, `user_id`, `email`, `payload`, `created_at` (the monolith's original value), `received_at`, `status` (`pending`, `sent` or `failed`), `attempts`, `next_attempt_at`, `lease_until`, `sent_at`, `paged_at`.
- `result_outbox`: `id`, `notification_id`, `status`, `attempts`, `published_at`.

### What happens when things fail

| Failure | Outcome |
|---|---|
| Caller's transaction rolls back | No row, no notification. |
| Old worker dies after MailRelay accepted, before its batch commit | Rows stay `pending` and are retried with the same key. MailRelay drops the repeat and the row becomes `sent`. |
| MailRelay times out but had accepted | The retry reuses the key and gets success. No duplicate. |
| MailRelay down | 5 attempts over about 15 minutes, then `failed` with a page. Nothing waits on an ack. |
| Broker down | Relay publish or confirmation fails, the transaction rolls back, and rows stay `pending`. The relay retries every second. Enqueue is only a local insert, so checkout is unaffected. Rows already `handed_off` keep sending in the service. |
| Relay crashes after broker confirm, before commit | The row stays `pending` and is re-published. The service ignores the copy because the id is its primary key. |
| Broker redelivers a message to the service | Primary-key conflict, no-op, acknowledged. An already-`sent` row is never sent again. |
| Service crashes after MailRelay accepts, before the row is updated | The lease expires and the row is re-claimed and re-sent with the same key. MailRelay returns success and the row becomes `sent`. |
| Service crash or restart | Leases expire and rows are re-claimed. Unconsumed messages wait in the broker. |
| Service down for a long time | Messages wait in the broker and the staleness alarm fires. |
| Broker redelivers a result | The `status = 'handed_off'` guard makes it a no-op. |
| Relay row locked by the old worker | `SKIP LOCKED` skips it. The relay takes it next pass if it is still `pending`. |
| Message lost | The staleness alarm fires. Recovery is the break-glass procedure in step 6. |
| Flag read fails in the old worker | The worker treats it as `monolith`, the safe default. |

**Residual risk.** Crash protection leans on MailRelay's 24-hour key window, while our whole retry cycle is about 15 minutes. A crash combined with a delay of more than 24 hours could duplicate. The 30-minute staleness alarm and the 24-hour limit on reclaim keep that window from being reached in practice.

## Rollout steps

Steps are in shipping order.

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

### 1. Pass `idempotency_key` from the old worker

- **Starts it:** a merge and deploy, before anything else exists. No type may move until it has been live everywhere.
- **Change:** in `_deliver`, call `mailrelay.send(to=..., subject=..., body=..., idempotency_key=row.id)`. Batching, retries and statuses stay the same.
- **State:** the monolith table. MailRelay remembers keys for 24 hours.
- **Failures:** as in the failure table. MailRelay down is unchanged.
- **Verify:** duplicate-email support tickets drop to roughly zero over a week. MailRelay returns success on a dropped repeat, so its drop count is not visible. Tickets are the signal.

### 2. Monolith groundwork, dark

- **Starts it:** deploy after step 1. Everything is inert until a flag flips.
- **Changes:**
  - Schema (additive): allow `status = 'handed_off'` and add `handed_off_at timestamptz`.
  - Create the three route flags, all `monolith`.
  - Each worker loop reads the flags and adds `AND type NOT IN (<types routed to service>)` to its `SELECT`. Nothing else in `run_worker` or `_deliver` changes.
- **Data moves:** none. State is the monolith database and flags.
- **Failures:** mixed versions are the main danger. An old-build instance has no filter and would keep sending a type already flipped. No flag may flip until a per-instance build-version metric shows every instance on the new build.

### 3. Build and deploy the Notification Service, dark

- **Starts it:** built in parallel with step 2. Deployed separately with its own database and no traffic.
- **Build:** the consumer, sender, result publisher and failure pager described under "How it runs", with the database above.
- **State:** entirely in the service database.
- **Failures:** as in the failure table.
- **Verify:** in staging, send synthetic notifications to the MailRelay sandbox. Cover success, MailRelay errors, a crash between send and record, and a duplicated message.

### 4. Monolith relay and result consumer, dark

- **Starts it:** deploy after steps 2 and 3. With all flags on `monolith` the relay finds no rows.
- **Build:** the relay, result consumer and staleness alarm described under "How it runs".
- **Data moves:** rows go out as messages and results come back as messages. The monolith table holds the durable record. The broker holds only in-transit copies.
- **Failures:** as in the failure table.
- **Verify:** staging, then a production dry run.

### 5. Move `shipping_update`

- **Starts it:** set `notifications.route.shipping_update = service`. Preconditions: steps 1 to 4 are done and every instance runs the new build.
- **Flow:** the carrier webhook enqueues a `pending` row. The old worker now excludes the type, so the relay hands the row off and the service sends it. The result comes back and the monolith row becomes `sent`.
- **Rows in flight at the flip:** instances may disagree on the flag for up to 10 s. A `pending` row, including one mid-retry, is claimed under a row lock by exactly one of the worker or the relay, and the loser skips it. If the worker has sent a row but not committed, the relay skips it until the commit lands. If the worker crashes before that commit, the row stays `pending` and may go to the service. The service re-sends with the same key and MailRelay drops it.
- **Failures:** as in the failure table.
- **Gate:** at least 3 days on the service, counted from the last flip to `service` (see step 6), before step 7. Watch send success rate, backlog, and p50 and p99 enqueue-to-MailRelay time.

### 6. Rollback drill, and the rollback rule for every type

- **Starts it:** in the first day or two after step 5, in a quiet period, flip `notifications.route.shipping_update = monolith`. Watch for 15 minutes, then flip back to `service`. The 3-day soak in step 5 restarts from this last flip.
- **Normal rollback:** one flag flip. Within 10 s the old worker starts claiming new `pending` rows of that type, and within about 15 s in total the relay stops claiming them. In-flight rows are not moved: `handed_off` rows finish in the service with the same retry policy, and `pending` rows go to whichever side claims them first. Nothing is lost or re-sent, because ownership never changes after a row leaves `pending`.
- **Break-glass, when the service itself is broken.** `handed_off` rows are stuck, because the monolith will not touch them.
  1. Pause the service consumer and sender for that type with the service's own switch, and let the result consumer drain.
  2. An operator sets rows back to `pending` only if they are under 24 hours old (by `created_at`) and still `handed_off`. The old worker then sends them with the same key. If the service sent one just before the pause, MailRelay drops the repeat.
  3. Review older `handed_off` rows manually, because the key has expired.
  4. Known gap: reclaimed rows restart at `attempts = 0`, giving slightly more than 5 attempts. This is only for incidents.
- **Verify during the drill:** zero duplicate emails. Every row created during the drill ends `sent` or `failed`. The `handed_off` rows finish on the service.

### 7. Move `order_confirmed`

- **Starts it:** at least 3 days after the last `shipping_update` flip to `service`, with nothing from steps 5 and 6 failing. Set `notifications.route.order_confirmed = service`.
- **Flow, data, state, failures and rollback:** as in steps 5 and 6. The trigger is checkout committing an order, 12,000 a day. A broker or service problem does not affect checkout.
- **Gate:** at least 3 days on the service, then step 8.

### 8. Latency gate for `password_reset`

- **Starts it:** at the end of `order_confirmed`'s 3 days on the service.
- **Metric:** the service records `sent_at - created_at`, where `created_at` is the monolith row's creation time carried in the message.
- **Pass:** over the whole 3-day window, p99 is under 60 s, counting all sends including retried ones. At about 12,000 a day that is about 36,000 samples, enough for p99. Also record the first-attempt-only distribution, to tell a slow pipeline from MailRelay incidents.
- **If it fails:** do not move `password_reset`. Fix the cause and restart the 3-day measurement.
- **Expected budget:** relay poll 1 s, publish and confirm well under 1 s, consume and insert under 1 s, sender poll 1 s, plus the MailRelay call. That leaves a lot of headroom.

### 9. Move `password_reset`

- **Starts it:** step 8 passes. Set `notifications.route.password_reset = service`.
- **Flow, data, state and failures:** as in step 5. Add a standing alert for the 60 s requirement, for example p99 above 30 s over 15 minutes. The first response is the step 6 flip back to `monolith`. Rollback matters most here, because users are waiting.
- **Gate:** the service has run `password_reset` for 7 days with no rollback. Any flip back restarts the count.

### 10. Decommission the old worker

- **Starts it:** `password_reset` has run on the service for 7 days with p99 under 60 s.
- **Sequence:**
  1. Pre-checks: no `pending` rows for any type, no `handed_off` rows older than 30 minutes, and the worker and relay queues empty.
  2. Deploy with `run_worker` not started. The relay, result consumer, `enqueue_notification` and flags remain.
  3. Observe for a day. Pending rows should stay at zero and sends continue.
  4. Delete the old worker code (`run_worker`, `_deliver`, the old backoff constants) and the worker filter from step 2.
  5. In a separate later change, retire the per-type flags once nobody needs rollback.
- **Failures:** with no old worker, a service or broker outage makes rows accumulate as `pending` or `handed_off`. Checkout is unaffected and delivery resumes on recovery. After deletion there is no fallback sender, so recovery is a service fix. The break-glass procedure applies only if a worker is redeployed from history.

## Open questions

Confirm these before step 3 or 4:
- Does `templates.render(type, payload)` need anything beyond `type` and `payload`? The service has only those.
- Does the broker retain unconsumed messages longer than the longest service outage we plan to ride out?
- Does the service have its own on-call paging path?
- Reclaimed rows in break-glass restart at `attempts = 0`. This is accepted for now.
